"""Create a manual asset-verification audit record and image uploads."""

import json
import os
import uuid

import boto3
from botocore.config import Config

from shared_utils._response import _response
from shared_utils.claims import get_user_claims
from shared_utils.cors import handle_options_request, handle_request_metadata
from shared_utils.request import parse_json_body
from shared_utils.s3 import generate_presigned_upload_url, validate_upload_metadata
from shared_utils.to_human_date import get_local_now


REGION = os.getenv("AWS_REGION", "af-south-1")
BUCKET_NAME = os.getenv("IMAGES_BUCKET_NAME", "crud-nosql-app-images")
TABLE_USERS = "crud-nosql-app-users-table"
TABLE_ASSETS = "crud-nosql-app-assets-table"
TABLE_VERIFICATIONS = "crud-nosql-app-assets-verification-table"
MAX_IMAGES = 10

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table_users = dynamodb.Table(TABLE_USERS)
table_assets = dynamodb.Table(TABLE_ASSETS)
table_verifications = dynamodb.Table(TABLE_VERIFICATIONS)
s3 = boto3.client(
    "s3",
    region_name=REGION,
    config=Config(
        s3={"addressing_style": "virtual"},
        signature_version="s3v4",
        region_name=REGION,
    ),
)


def get_asset(asset_uuid):
    """Return the UUID-keyed asset, or ``None`` when it does not exist."""
    return table_assets.get_item(
        Key={"id": asset_uuid},
        ConsistentRead=True,
    ).get("Item")


def get_user_name(user_id, claims):
    """Resolve the verifier name as normal verification does."""
    user = table_users.get_item(Key={"id": user_id}).get("Item", {})
    full_name = " ".join(
        part
        for part in [user.get("name", ""), user.get("family_name", "")]
        if part
    ).strip()
    if full_name:
        return full_name

    return " ".join(
        part
        for part in [claims.get("name", ""), claims.get("family_name", "")]
        if part
    ).strip()


def validate_images(images):
    """Validate and normalize image descriptors supplied by the frontend."""
    images = validate_upload_metadata(images, owner_label="manual verification")
    if len(images) > MAX_IMAGES:
        raise ValueError(f"A maximum of {MAX_IMAGES} images is allowed")

    validated = []
    filenames = set()
    for image in images:
        filename = str(image.get("filename") or "").strip()
        content_type = str(image.get("content_type") or "").strip().lower()

        if (
            not filename
            or filename in (".", "..")
            or any(char in filename for char in ("/", "\\", "\r", "\n", "\x00"))
        ):
            raise ValueError("Every image requires a safe filename")
        if filename in filenames:
            raise ValueError(f"Duplicate image filename: {filename}")
        if (
            not content_type.startswith("image/")
            or any(char in content_type for char in ("\r", "\n"))
        ):
            raise ValueError("Every image requires a valid image content_type")

        filenames.add(filename)
        validated.append({"filename": filename, "content_type": content_type})

    return validated


def build_uploads(asset_uuid, verification_id, images):
    """Return upload instructions in the existing frontend-compatible shape."""
    uploads = []
    for image in images:
        key = (
            f"verification/{asset_uuid}/{verification_id}/images/"
            f"{image['filename']}"
        )
        uploads.append(
            {
                "type": "images",
                "filename": image["filename"],
                "content_type": image["content_type"],
                "key": key,
                "url": generate_presigned_upload_url(
                    s3=s3,
                    bucket_name=BUCKET_NAME,
                    key=key,
                    content_type=image["content_type"],
                ),
            }
        )
    return uploads


def lambda_handler(event, context):
    """Handle ``POST /api/assets/{id}/verify-manual``."""
    del context
    method, headers = handle_request_metadata(
        event,
        allowed_methods="POST,OPTIONS",
    )
    options_response = handle_options_request(method, headers)
    if options_response:
        return options_response

    try:
        claims = get_user_claims(event)
        user_id = claims.get("sub")
        if not user_id:
            return _response(401, {"message": "Unauthorized"}, headers)

        asset_uuid = str((event.get("pathParameters") or {}).get("id") or "").strip()
        if not asset_uuid:
            return _response(400, {"message": "Missing asset id"}, headers)

        body = parse_json_body(event)
        body_asset_id = str(body.get("id") or "").strip()
        if body_asset_id and body_asset_id != asset_uuid:
            return _response(
                400,
                {"message": "Request body id must match the route asset id"},
                headers,
            )

        reason = str(body.get("reason") or "").strip()
        if not reason:
            return _response(
                400,
                {"message": "Manual verification reason is required"},
                headers,
            )

        images = validate_images(body.get("images", []))
        asset = get_asset(asset_uuid)
        if not asset:
            return _response(404, {"message": "Asset not found"}, headers)

        verifier_name = get_user_name(user_id, claims)
        if not verifier_name:
            return _response(
                400,
                {"message": "Authenticated user does not have a display name"},
                headers,
            )

        location = str(body.get("location") or asset.get("location") or "").strip()
        verification_id = str(uuid.uuid4())
        verification_created = get_local_now()
        verification_asset_id = str(asset.get("assetID") or asset_uuid)
        uploads = build_uploads(asset_uuid, verification_id, images)

        verification_item = {
            "assetID": verification_asset_id,
            "assetUuid": asset_uuid,
            "verificationCreated": verification_created,
            "id": verification_id,
            "verified_by": verifier_name,
            "verifier_id": user_id,
            "verification_method": "manual",
            "verification_status": "verified",
            "manual_verification_reason": reason,
            "location": location,
            "images": [],
        }

        table_verifications.put_item(
            Item=verification_item,
            ConditionExpression=(
                "attribute_not_exists(assetID) AND "
                "attribute_not_exists(verificationCreated)"
            ),
        )

        return _response(
            200,
            {
                "message": f"Asset {asset_uuid} successfully verified manually",
                "verification_id": verification_id,
                "verification_created": verification_created,
                "presigned_urls": uploads,
            },
            headers,
        )

    except ValueError as exc:
        return _response(400, {"message": str(exc)}, headers)
    except Exception as exc:
        print(
            "Manual verification failed:",
            json.dumps(
                {
                    "asset_uuid": (event.get("pathParameters") or {}).get("id"),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            ),
        )
        return _response(500, {"message": "Internal server error"}, headers)
