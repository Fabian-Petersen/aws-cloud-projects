import json

import boto3
from boto3.dynamodb.conditions import Key
from botocore.config import Config
from botocore.exceptions import ClientError

from shared_utils._response import _response
from shared_utils.cors import handle_options_request, handle_request_metadata
from shared_utils.dynamodb import query_first
from shared_utils.request import parse_json_body
from shared_utils.s3 import generate_presigned_upload_url
from shared_utils.to_human_date import get_local_now


REGION = "af-south-1"
TABLE_NAME = "crud-nosql-app-assets-disposal-table"
BUCKET_NAME = "crud-nosql-app-images"

dynamodb = boto3.resource("dynamodb", region_name=REGION)
s3 = boto3.client(
    "s3",
    region_name=REGION,
    config=Config(
        s3={"addressing_style": "virtual"},
        signature_version="s3v4",
        region_name=REGION,
    ),
)

table = dynamodb.Table(TABLE_NAME)


EDITABLE_FIELDS = (
    "description",
    "disposalReason",
    "location",
    "expectedDisposalDate",
    "assets",
)
PENDING_FIELDS = {
    "description",
    "disposalReason",
    "location",
    "expectedDisposalDate",
}


def lambda_handler(event, context):
    print("event:", json.dumps(event))

    """
    Update an existing disposal request.

    Expected path:
        /api/disposals/{id}

    Expected body:
        {
            "description": "...",
            "disposalReason": "sell",
            "location": "central services",
            "expectedDisposalDate": "2026-10-16",
            "assets": [...],
            "deleted_image_keys": [...]
        }
    """
    method, headers = handle_request_metadata(
        event,
        allowed_methods="PUT,OPTIONS",
    )
    options_response = handle_options_request(method, headers)
    if options_response:
        return options_response

    try:
        disposal_id = (event.get("pathParameters") or {}).get("id")

        if not disposal_id:
            return _response(
                400,
                {"message": "Disposal id is required"},
                headers,
            )

        body, error = _parse_body(event, headers)

        if error:
            return error

        validation_error = _validate_payload(body, headers)

        if validation_error:
            return validation_error

        existing_disposal = _get_disposal(disposal_id)

        if not existing_disposal:
            return _response(
                404,
                {"message": "Disposal request not found"},
                headers,
            )

        disposal_created = existing_disposal.get("disposalCreated")

        if not disposal_created:
            print(
                json.dumps(
                    {
                        "stage": "missing_sort_key",
                        "disposalId": disposal_id,
                    }
                )
            )

            return _response(
                500,
                {"message": "Disposal request has invalid stored data"},
                headers,
            )

        deleted_image_keys = body.get("deleted_image_keys", [])

        unsafe_key = _find_unsafe_image_key(
            disposal_id,
            deleted_image_keys,
            existing_disposal,
        )

        if unsafe_key:
            return _response(
                400,
                {
                    "message": (
                        "One or more deleted image keys "
                        "do not belong to this disposal request"
                    )
                },
                headers,
            )

        update_body = dict(body)
        presigned_urls = []
        if "assets" in body or deleted_image_keys:
            reconciled_assets, presigned_urls = _reconcile_assets(
                disposal_id=disposal_id,
                submitted_assets=body.get("assets"),
                existing_disposal=existing_disposal,
                deleted_image_keys=set(deleted_image_keys),
            )
            update_body["assets"] = reconciled_assets

        updated_disposal = _update_disposal(
            disposal_id=disposal_id,
            disposal_created=disposal_created,
            existing_disposal=existing_disposal,
            body=update_body,
        )

        if deleted_image_keys:
            _delete_images(
                disposal_id=disposal_id,
                image_keys=deleted_image_keys,
            )

        print(
            json.dumps(
                {
                    "stage": "update_complete",
                    "disposalId": disposal_id,
                    "assetCount": len(
                        update_body.get(
                            "assets",
                            existing_disposal.get("assets") or [],
                        )
                    ),
                    "deletedImageCount": len(deleted_image_keys),
                    "newImageCount": len(presigned_urls),
                },
                default=str,
            )
        )

        return _response(
            200,
            {
                "message": "Disposal request updated successfully",
                "data": updated_disposal,
                "presigned_urls": presigned_urls,
                "deleted_image_keys": deleted_image_keys,
            },
            headers,
        )

    except ValueError as exc:
        return _response(
            400,
            {"message": str(exc)},
            headers,
        )

    except ClientError as exc:
        print(
            json.dumps(
                {
                    "stage": "aws_error",
                    "error": str(exc),
                },
                default=str,
            )
        )

        error_code = exc.response.get("Error", {}).get("Code")
        if error_code == "ConditionalCheckFailedException":
            return _response(
                404,
                {"message": "Disposal request not found"},
                headers,
            )

        return _response(
            500,
            {"message": "Unable to update disposal request"},
            headers,
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "stage": "unhandled_error",
                    "error": str(exc),
                },
                default=str,
            )
        )

        return _response(
            500,
            {"message": "Internal server error"},
            headers,
        )


def _parse_body(event, headers):
    """Parse the incoming JSON request body."""

    try:
        body = parse_json_body(event)
    except ValueError as exc:
        return None, _response(
            400,
            {"message": str(exc)},
            headers,
        )

    return body, None


def _validate_payload(body, headers):
    """Perform minimal backend validation."""

    supplied_editable_fields = set(EDITABLE_FIELDS).intersection(body.keys())

    if not supplied_editable_fields and "deleted_image_keys" not in body:
        return _response(
            400,
            {"message": "No editable disposal fields supplied"},
            headers,
        )

    if "description" in body and not isinstance(body["description"], str):
        return _response(
            400,
            {"message": "description must be a string"},
            headers,
        )

    if (
        "disposalReason" in body
        and not isinstance(body["disposalReason"], str)
    ):
        return _response(
            400,
            {"message": "disposalReason must be a string"},
            headers,
        )

    if "location" in body and not isinstance(body["location"], str):
        return _response(
            400,
            {"message": "location must be a string"},
            headers,
        )

    if (
        "expectedDisposalDate" in body
        and not isinstance(body["expectedDisposalDate"], str)
    ):
        return _response(
            400,
            {"message": "expectedDisposalDate must be a string"},
            headers,
        )

    if "assets" in body:
        if not isinstance(body["assets"], list):
            return _response(
                400,
                {"message": "assets must be an array"},
                headers,
            )

        if not body["assets"]:
            return _response(
                400,
                {"message": "At least one asset is required"},
                headers,
            )

        for asset in body["assets"]:
            if not isinstance(asset, dict):
                return _response(
                    400,
                    {"message": "Each asset must be an object"},
                    headers,
                )

            if not asset.get("assetID") and not (
                asset.get("equipment") and asset.get("area")
            ):
                return _response(
                    400,
                    {
                        "message": (
                            "Unidentified assets require area and equipment"
                        )
                    },
                    headers,
                )

            if "images" in asset and not isinstance(
                asset["images"],
                list,
            ):
                return _response(
                    400,
                    {"message": "Asset images must be an array"},
                    headers,
                )

    deleted_image_keys = body.get("deleted_image_keys", [])

    if not isinstance(deleted_image_keys, list):
        return _response(
            400,
            {"message": "deleted_image_keys must be an array"},
            headers,
        )

    if not all(
        isinstance(key, str) and bool(key.strip())
        for key in deleted_image_keys
    ):
        return _response(
            400,
            {
                "message": (
                    "Each deleted_image_keys value must be a non-empty string"
                )
            },
            headers,
        )

    return None


def _find_existing_asset(existing_assets, submitted_asset, position):
    """Match a submitted asset to its stored image collection."""

    submitted_index = submitted_asset.get("assetIndex", position)
    for asset in existing_assets:
        if (
            isinstance(asset, dict)
            and asset.get("assetIndex") == submitted_index
        ):
            return asset

    submitted_asset_id = str(submitted_asset.get("assetID") or "").strip()
    if submitted_asset_id:
        for asset in existing_assets:
            if (
                isinstance(asset, dict)
                and str(asset.get("assetID") or "").strip()
                == submitted_asset_id
            ):
                return asset

    return {}


def _validate_new_image(file_info, owner_label):
    """Validate one new-image descriptor and return normalized metadata."""

    if not isinstance(file_info, dict):
        raise ValueError(f"Every upload for {owner_label} must be an object")

    filename = file_info.get("filename")
    if not isinstance(filename, str):
        raise ValueError(
            f"Every upload for {owner_label} requires a valid filename"
        )
    filename = filename.strip()
    if (
        not filename
        or filename in (".", "..")
        or any(char in filename for char in ("/", "\\", "\r", "\n", "\x00"))
    ):
        raise ValueError(
            f"Every upload for {owner_label} requires a valid filename"
        )

    content_type = file_info.get(
        "content_type",
        "application/octet-stream",
    )
    if (
        not isinstance(content_type, str)
        or not content_type.strip()
        or "/" not in content_type
        or "\r" in content_type
        or "\n" in content_type
    ):
        raise ValueError(
            f"Every upload for {owner_label} requires a valid content_type"
        )

    return filename, content_type.strip()


def _reconcile_assets(
    disposal_id,
    submitted_assets,
    existing_disposal,
    deleted_image_keys,
):
    """Preserve stored images and sign uploads requested by image metadata.

    New image descriptors are deliberately not stored in DynamoDB. After the
    browser uploads each file with the returned URL, s3FileUploadLambda appends
    the completed ``bucket``/``key`` metadata to the matching asset.
    """

    existing_assets = [
        asset
        for asset in existing_disposal.get("assets") or []
        if isinstance(asset, dict)
    ]
    has_submitted_assets = submitted_assets is not None
    source_assets = submitted_assets if has_submitted_assets else existing_assets
    reconciled_assets = []
    presigned_urls = []

    for position, submitted_asset in enumerate(source_assets):
        existing_asset = _find_existing_asset(
            existing_assets,
            submitted_asset,
            position,
        )
        retained_images = [
            image
            for image in existing_asset.get("images") or []
            if (
                isinstance(image, dict)
                and isinstance(image.get("key"), str)
                and image["key"]
                and image["key"] not in deleted_image_keys
            )
        ]
        retained_keys = {image["key"] for image in retained_images}
        new_keys = set()

        requested_images = (
            submitted_asset.get("images") or []
            if has_submitted_assets
            else []
        )
        for file_info in requested_images:
            if not isinstance(file_info, dict):
                raise ValueError("Each asset image must be an object")

            existing_key = file_info.get("key")
            if existing_key:
                if existing_key not in retained_keys:
                    raise ValueError(
                        "One or more retained image keys do not belong "
                        "to the submitted asset"
                    )
                continue

            owner_label = f"asset {position}"
            filename, content_type = _validate_new_image(
                file_info,
                owner_label,
            )
            key = (
                f"disposals/{disposal_id}/assets/{position}/"
                f"images/{filename}"
            )
            if key in retained_keys:
                raise ValueError(
                    "Delete the existing image before uploading another "
                    "image with the same filename"
                )
            if key in new_keys:
                raise ValueError(
                    f"Duplicate new image filename for asset {position}: "
                    f"{filename}"
                )
            new_keys.add(key)

            upload = {
                "type": "images",
                "assetIndex": position,
                "filename": filename,
                "content_type": content_type,
                "key": key,
                "url": generate_presigned_upload_url(
                    s3=s3,
                    bucket_name=BUCKET_NAME,
                    key=key,
                    content_type=content_type,
                ),
            }
            asset_id = str(submitted_asset.get("assetID") or "").strip()
            if asset_id:
                upload["assetID"] = asset_id
            presigned_urls.append(upload)

        reconciled_asset = {
            key: value
            for key, value in submitted_asset.items()
            if key != "images"
        }
        # S3 object keys use the list position, so keep the stored index aligned.
        reconciled_asset["assetIndex"] = position
        reconciled_asset["images"] = retained_images
        reconciled_assets.append(reconciled_asset)

    return reconciled_assets, presigned_urls


def _get_disposal(disposal_id):
    """
    Retrieve the disposal request.

    disposalId is the partition key and disposalCreated is the sort key,
    therefore query is used to resolve the full DynamoDB key.
    """

    return query_first(
        table,
        KeyConditionExpression=Key("disposalId").eq(disposal_id),
        ProjectionExpression=(
            "disposalId, disposalCreated, #pending, assets"
        ),
        ExpressionAttributeNames={"#pending": "pending"},
    )


def _update_disposal(
    disposal_id,
    disposal_created,
    existing_disposal,
    body,
):
    """Update only explicitly permitted disposal fields."""

    update_fields = {
        field: body[field]
        for field in EDITABLE_FIELDS
        if field in body
    }
    pending = dict(existing_disposal.get("pending") or {})
    pending_changed = False
    for field in PENDING_FIELDS:
        if field in body:
            pending[field] = body[field]
            pending_changed = True
    if pending_changed:
        update_fields["pending"] = pending
    update_fields["dateUpdated"] = get_local_now()

    update_parts = []
    expression_names = {}
    expression_values = {}

    for index, (field, value) in enumerate(update_fields.items()):
        name_token = f"#field{index}"
        value_token = f":value{index}"

        update_parts.append(
            f"{name_token} = {value_token}"
        )

        expression_names[name_token] = field
        expression_values[value_token] = value

    response = table.update_item(
        Key={
            "disposalId": disposal_id,
            "disposalCreated": disposal_created,
        },
        UpdateExpression=(
            "SET " + ", ".join(update_parts)
        ),
        ExpressionAttributeNames=expression_names,
        ExpressionAttributeValues=expression_values,
        ConditionExpression=(
            "attribute_exists(disposalId) "
            "AND attribute_exists(disposalCreated)"
        ),
        ReturnValues="ALL_NEW",
    )

    return response.get("Attributes", {})


def _find_unsafe_image_key(
    disposal_id,
    image_keys,
    existing_disposal,
):
    """
    Prevent arbitrary S3 object deletion.
    """

    allowed_prefix = f"disposals/{disposal_id}/assets/"
    current_image_keys = {
        image.get("key")
        for asset in existing_disposal.get("assets") or []
        if isinstance(asset, dict)
        for image in asset.get("images") or []
        if isinstance(image, dict) and image.get("key")
    }

    for key in image_keys:
        if key not in current_image_keys or not key.startswith(allowed_prefix):
            print(
                json.dumps(
                    {
                        "stage": "unsafe_image_key",
                        "disposalId": disposal_id,
                        "key": key,
                    }
                )
            )

            return key

    return None


def _delete_images(
    disposal_id,
    image_keys,
):
    """Delete images explicitly removed by the user."""

    for key in image_keys:
        print(
            json.dumps(
                {
                    "stage": "delete_image",
                    "disposalId": disposal_id,
                    "key": key,
                }
            )
        )

        s3.delete_object(
            Bucket=BUCKET_NAME,
            Key=key,
        )
