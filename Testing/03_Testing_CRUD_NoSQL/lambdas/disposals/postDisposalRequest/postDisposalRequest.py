import uuid
import json

import boto3
from boto3.dynamodb.conditions import Key
from botocore.config import Config

from shared_utils._response import _response
from shared_utils.claims import get_requestor_identity
from shared_utils.cors import handle_options_request, handle_request_metadata
from shared_utils.dynamodb import normalize_string, query_first
from shared_utils.request import (
    parse_json_body,
    require_fields,
    require_non_empty_list,
)
from shared_utils.s3 import generate_presigned_upload_url, validate_upload_metadata
from shared_utils.to_human_date import get_local_now


REGION = "af-south-1"
DISPOSAL_TABLE_NAME = "crud-nosql-app-assets-disposal-table"
ASSETS_TABLE_NAME = "crud-nosql-app-assets-table"
BUCKET_NAME = "crud-nosql-app-images"

dynamodb = boto3.resource("dynamodb", region_name=REGION)
disposal_table = dynamodb.Table(DISPOSAL_TABLE_NAME)
assets_table = dynamodb.Table(ASSETS_TABLE_NAME)
s3 = boto3.client(
    "s3",
    region_name=REGION,
    config=Config(
        s3={"addressing_style": "virtual"},
        signature_version="s3v4",
        region_name=REGION,
    ),
)


def _get_registered_asset(asset_id):
    """Return the registered asset matching ``asset_id``, or ``None``.

    The lookup uses ``AssetIDIndex`` because the assets table is keyed by its
    internal ``id`` field rather than the user-facing asset ID.
    """
    return query_first(
        assets_table,
        IndexName="AssetIDIndex",
        KeyConditionExpression=Key("assetID").eq(asset_id),
    )


def _validate_asset_eligibility(registered_asset):
    """Validate a registered asset against future disposal status rules.

    No authoritative eligibility statuses exist yet, so this currently returns
    the asset unchanged and provides a single extension point for that rule.
    """
    return registered_asset


def _validate_request(data):
    """Validate disposal-level fields, asset objects, and duplicate IDs.

    Unidentified assets are allowed, so only non-empty ``assetID`` values
    participate in duplicate detection.

    Raises:
        ValueError: If required data is missing or an identified asset repeats.
    """
    require_fields(
        data,
        ["location", "expectedDisposalDate", "disposalReason", "assets"],
    )
    assets = require_non_empty_list(
        data,
        "assets",
        "At least one asset is required",
    )

    seen_asset_ids = set()
    for asset in assets:
        if not isinstance(asset, dict):
            raise ValueError("Every asset must be a JSON object")
        asset_id = str(asset.get("assetID") or "").strip()
        if not asset_id:
            continue
        duplicate_key = asset_id.casefold()
        if duplicate_key in seen_asset_ids:
            raise ValueError(f"Duplicate assetID: {asset_id}")
        seen_asset_ids.add(duplicate_key)


def _build_asset(asset, asset_index, disposal_id):
    """Normalize one asset and create its requested image-upload URLs.

    Registered assets are enriched from DynamoDB. Unidentified assets retain
    frontend-provided descriptive fields and are not assigned an ``assetID``.

    Returns:
        tuple: ``(normalized_asset, presigned_uploads)`` for the response.

    Raises:
        LookupError: If a supplied ``assetID`` is not registered.
        ValueError: If unidentified asset or image metadata is invalid.
    """
    asset_id = str(asset.get("assetID") or "").strip()
    if asset_id:
        registered_asset = _get_registered_asset(asset_id)
        if not registered_asset:
            raise LookupError(asset_id)
        _validate_asset_eligibility(registered_asset)
        equipment = registered_asset.get("equipment")
        area = registered_asset.get("area")
    else:
        equipment = asset.get("equipment")
        area = asset.get("area")
        if not equipment or not area:
            raise ValueError(
                f"Unidentified asset {asset_index} requires area and equipment"
            )

    processed_asset = {
        "assetIndex": asset_index,
        "equipment": equipment,
        "area": normalize_string(area),
        "assetIssueReason": normalize_string(asset.get("assetIssueReason")),
        "assetIssueDetails": asset.get("assetIssueDetails", ""),
        "images": [],
    }
    if asset_id:
        processed_asset["assetID"] = asset_id

    presigned_urls = []
    for file_info in validate_upload_metadata(
        asset.get("images", []),
        owner_label=f"asset {asset_index}",
    ):
        filename = str(file_info["filename"]).strip()
        content_type = file_info.get(
            "content_type",
            "application/octet-stream",
        )
        key = (
            f"disposals/{disposal_id}/assets/{asset_index}/"
            f"images/{filename}"
        )
        upload = {
            "type": "images",
            "assetIndex": asset_index,
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
        if asset_id:
            upload["assetID"] = asset_id
        presigned_urls.append(upload)

    return processed_asset, presigned_urls


def lambda_handler(event, context):
    """Create one pending disposal request containing all submitted assets."""
    print("event:", json.dumps(event))

    method, headers = handle_request_metadata(
        event,
        allowed_methods="POST,OPTIONS",
    )
    options_response = handle_options_request(method, headers)
    if options_response:
        return options_response

    try:
        data = parse_json_body(event)
        _validate_request(data)

        requestor = get_requestor_identity(event)
        requestor_sub = requestor["requestorSub"]
        if not requestor_sub:
            return _response(401, {"message": "Unauthorized"}, headers)

        requestor_name = requestor["requestorName"]
        requested_by = requestor["requestedBy"]
        requestor_email = requestor["requestorEmail"]

        disposal_id = str(uuid.uuid4())
        disposal_created = get_local_now()
        processed_assets = []
        presigned_urls = []
        for asset_index, asset in enumerate(data["assets"]):
            processed_asset, asset_uploads = _build_asset(
                asset,
                asset_index,
                disposal_id,
            )
            processed_assets.append(processed_asset)
            presigned_urls.extend(asset_uploads)

        location = normalize_string(data["location"])
        description = data.get("description", "")
        disposal_reason = data["disposalReason"]
        expected_disposal_date = data["expectedDisposalDate"]
        schedule_name = f"disposal-{disposal_id}-timeout"

        item = {
            "disposalId": disposal_id,
            "disposalCreated": disposal_created,
            "status": "pending",
            "dateUpdated": disposal_created,
            "requestorSub": requestor_sub,
            "requestorEmail": requestor_email,
            "requestedBy": normalize_string(requested_by),
            "requestorName": normalize_string(requestor_name),
            "location": location,
            "expectedDisposalDate": expected_disposal_date,
            "disposalReason": disposal_reason,
            "description": description,
            "approvalReminderCount": 0,
            "schedule_name": schedule_name,
            "assets": processed_assets,
            "pending": {
                "requestedBy": normalize_string(requested_by),
                "requestorName": normalize_string(requestor_name),
                "requestorSub": requestor_sub,
                "description": description,
                "disposalReason": disposal_reason,
                "location": location,
                "expectedDisposalDate": expected_disposal_date,
            },
            "approved": None,
            "disposed": None,
            "cancelled": None,
            "rejected": None,
            "expired": None,
        }

        disposal_table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(disposalId)",
        )

        return _response(
            200,
            {"data": item, "presigned_urls": presigned_urls},
            headers,
        )
    except ValueError as exc:
        return _response(400, {"message": str(exc)}, headers)
    except LookupError as exc:
        asset_id = exc.args[0] if exc.args else ""
        return _response(
            404,
            {"message": f"Asset not found: {asset_id}"},
            headers,
        )
    except Exception as exc:
        print("Error creating disposal request:", repr(exc))
        return _response(500, {"message": "Internal server error"}, headers)
