"""Update an asset and reconcile its existing and newly uploaded images."""

import json
import os

import boto3
from botocore.config import Config


TABLE_NAME = os.getenv("ASSETS_TABLE_NAME", "crud-nosql-app-assets-table")
BUCKET_NAME = os.getenv("IMAGES_BUCKET_NAME", "crud-nosql-app-images")
AWS_REGION = os.getenv("AWS_REGION", "af-south-1")
MAX_IMAGES = 10

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)
s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    config=Config(
        s3={"addressing_style": "virtual"},
        signature_version="s3v4",
        region_name=AWS_REGION,
    ),
)

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "DELETE,OPTIONS,PUT",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With",
    "Access-Control-Allow-Credentials": "true",
}

UPDATABLE_FIELDS = {
    "location",
    "business_unit",
    "area",
    "equipment",
    "assetType",
    "category",
    "replacementValue",
    "assetID",
    "condition",
    "serialNumber",
    "additional_notes",
}

OPTIONAL_SPARSE_FIELDS = {"assetID", "serialNumber"}


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": HEADERS,
        "body": json.dumps(body),
    }


def _validate_new_images(images):
    if not isinstance(images, list):
        raise ValueError("images must be an array")

    validated = []
    filenames = set()

    for image in images:
        if not isinstance(image, dict):
            raise ValueError("Each new image must be an object")

        filename = str(image.get("filename") or "").strip()
        content_type = str(
            image.get("content_type") or "application/octet-stream"
        ).strip()

        if not filename or "/" in filename or "\\" in filename:
            raise ValueError("Each new image requires a safe filename")

        if filename in filenames:
            raise ValueError(f"Duplicate new image filename: {filename}")

        filenames.add(filename)
        validated.append(
            {"filename": filename, "content_type": content_type}
        )

    return validated


def _validate_deleted_keys(asset_uuid, deleted_keys, current_images):
    if not isinstance(deleted_keys, list) or not all(
        isinstance(key, str) for key in deleted_keys
    ):
        raise ValueError("deleted_image_keys must be an array of strings")

    requested = set(deleted_keys)
    current_keys = {
        image.get("key")
        for image in current_images
        if isinstance(image, dict) and image.get("key")
    }
    prefix = f"assets/{asset_uuid}/"

    invalid_keys = [
        key
        for key in requested
        if key not in current_keys or not key.startswith(prefix)
    ]
    if invalid_keys:
        raise ValueError("One or more images do not belong to this asset")

    return requested


def _build_update_expression(update_fields, remove_fields):
    parts = []
    expression_names = {}
    expression_values = {}

    if update_fields:
        assignments = []
        for index, (field, value) in enumerate(update_fields.items()):
            name = f"#field{index}"
            value_name = f":value{index}"
            expression_names[name] = field
            expression_values[value_name] = value
            assignments.append(f"{name} = {value_name}")
        parts.append("SET " + ", ".join(assignments))

    if remove_fields:
        names = []
        offset = len(expression_names)
        for index, field in enumerate(sorted(remove_fields), start=offset):
            name = f"#field{index}"
            expression_names[name] = field
            names.append(name)
        parts.append("REMOVE " + ", ".join(names))

    return " ".join(parts), expression_names, expression_values


def _presign_uploads(asset_uuid, new_images):
    uploads = []

    for image in new_images:
        key = f"assets/{asset_uuid}/{image['filename']}"
        url = s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": BUCKET_NAME,
                "Key": key,
                "ContentType": image["content_type"],
            },
            ExpiresIn=3600,
        )
        uploads.append(
            {
                "filename": image["filename"],
                "url": url,
                "key": key,
                "content_type": image["content_type"],
                "type": "images",
            }
        )

    return uploads


def lambda_handler(event, context):
    del context

    try:
        asset_uuid = (event.get("pathParameters") or {}).get("id")
        if not asset_uuid:
            return _response(400, {"message": "id (UUID) is required"})

        if not event.get("body"):
            return _response(400, {"message": "Request body is required"})

        body = json.loads(event["body"])
        if not isinstance(body, dict):
            return _response(400, {"message": "Request body must be an object"})

        existing = table.get_item(
            Key={"id": asset_uuid}, ConsistentRead=True
        ).get("Item")
        if not existing:
            return _response(404, {"message": "Asset not found"})

        current_images = existing.get("images", [])
        if not isinstance(current_images, list):
            current_images = []

        new_images = _validate_new_images(body.get("images", []))
        deleted_keys = _validate_deleted_keys(
            asset_uuid,
            body.get("deleted_image_keys", []),
            current_images,
        )
        retained_images = [
            image
            for image in current_images
            if not isinstance(image, dict) or image.get("key") not in deleted_keys
        ]

        retained_filenames = {
            image.get("filename")
            for image in retained_images
            if isinstance(image, dict) and image.get("filename")
        }
        duplicate_filenames = [
            image["filename"]
            for image in new_images
            if image["filename"] in retained_filenames
        ]
        if duplicate_filenames:
            return _response(
                400,
                {
                    "message": (
                        "Delete the existing image before uploading another "
                        "image with the same filename"
                    )
                },
            )

        if len(retained_images) + len(new_images) > MAX_IMAGES:
            return _response(
                400,
                {"message": f"A maximum of {MAX_IMAGES} images is allowed"},
            )

        update_fields = {
            key: value
            for key, value in body.items()
            if key in UPDATABLE_FIELDS
        }
        remove_fields = {
            field
            for field in OPTIONAL_SPARSE_FIELDS
            if field in update_fields
            and update_fields[field] in (None, "", 0)
        }
        for field in remove_fields:
            update_fields.pop(field, None)

        if deleted_keys:
            update_fields["images"] = retained_images

        if not update_fields and not remove_fields and not new_images:
            return _response(400, {"message": "No valid fields to update"})

        presigned_urls = _presign_uploads(asset_uuid, new_images)

        if update_fields or remove_fields:
            update_expression, names, values = _build_update_expression(
                update_fields, remove_fields
            )

            update_kwargs = {
                "Key": {"id": asset_uuid},
                "UpdateExpression": update_expression,
                "ExpressionAttributeNames": names,
                "ConditionExpression": "attribute_exists(id)",
                "ReturnValues": "ALL_NEW",
            }
            if values:
                update_kwargs["ExpressionAttributeValues"] = values

            result = table.update_item(**update_kwargs)
            updated_asset = result.get("Attributes", {})
        else:
            updated_asset = existing

        for key in deleted_keys:
            s3.delete_object(Bucket=BUCKET_NAME, Key=key)

        return _response(
            200,
            {
                "message": "Asset updated successfully",
                "asset": updated_asset,
                "presigned_urls": presigned_urls,
                "deleted_image_keys": sorted(deleted_keys),
            },
        )

    except (json.JSONDecodeError, ValueError) as exc:
        return _response(400, {"message": str(exc)})
    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": "Internal server error"})
