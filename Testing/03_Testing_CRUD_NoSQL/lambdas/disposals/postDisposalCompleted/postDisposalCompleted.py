"""Complete an approved disposal and prepare its evidence uploads."""

from decimal import Decimal
import json

import boto3
from boto3.dynamodb.conditions import Key
from botocore.config import Config
from botocore.exceptions import ClientError

from shared_utils._response import _response
from shared_utils.claims import get_requestor_identity
from shared_utils.cors import handle_options_request, handle_request_metadata
from shared_utils.dynamodb import query_first
from shared_utils.request import parse_json_body, require_fields
from shared_utils.s3 import generate_presigned_upload_url, validate_upload_metadata
from shared_utils.to_human_date import get_local_now


REGION = "af-south-1"
BUCKET_NAME = "crud-nosql-app-images"
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table_disposals = dynamodb.Table("crud-nosql-app-assets-disposal-table")
s3 = boto3.client(
    "s3", region_name=REGION,
    config=Config(s3={"addressing_style": "virtual"},
                  signature_version="s3v4"),
)


def get_disposal_by_id(disposal_id):
    """Find a disposal and return both key fields required for its update.

    Unlike transfers, disposalId is the table partition key, so no IdIndex
    lookup is needed. The frontend does not need to send disposalCreated.
    """
    return query_first(
        table_disposals,
        KeyConditionExpression=Key("disposalId").eq(disposal_id),
        ConsistentRead=True,
    )


def _validate_request(data):
    """Validate completion fields before querying DynamoDB or signing uploads."""
    # A truthy value alone could still be a number, object, or whitespace.
    require_fields(data, ["disposalMethod"])
    if not isinstance(data["disposalMethod"], str) or not data["disposalMethod"].strip():
        raise ValueError("disposalMethod must be a non-empty string")

    # Zero is valid, so do not use require_fields for cost. Reject booleans
    # explicitly because Python treats bool as a subclass of int.
    cost = data.get("disposalCost")
    if isinstance(cost, bool) or not isinstance(cost, (int, float, Decimal)):
        raise ValueError("disposalCost must be a non-negative number")
    # Boto3 requires Decimal for fractional DynamoDB numbers rather than float.
    cost = Decimal(str(cost))

    # NaN/infinity cannot represent a disposal cost or be stored by DynamoDB.
    if not cost.is_finite() or cost < 0:
        raise ValueError("disposalCost must be a finite non-negative number")

    # Notes are optional, but supplied values must be text (including "").
    if not isinstance(data.get("disposalNotes", ""), str):
        raise ValueError("disposalNotes must be a string")

    for field in ("disposalImages", "disposalDocuments"):
        files = data.get(field, [])

        # Omitted files default to []; reject null/objects and empty descriptors.
        if not isinstance(files, list):
            raise ValueError(f"{field} must be a list")

        for file_info in validate_upload_metadata(files, owner_label=field):
            filename = file_info["filename"]

            # Keep the filename inside the expected S3 folder and reject
            # control characters that would make upload metadata ambiguous.
            if (not isinstance(filename, str) or not filename.strip()
                    or filename.strip() in (".", "..")
                    or any(char in filename for char in ("/", "\\", "\r", "\n", "\x00"))):
                raise ValueError(
                    f"Every upload for {field} requires a valid filename")
            # The frontend must PUT using this same signed Content-Type.
            # This checks basic metadata shape, not the actual file contents.
            content_type = file_info.get("content_type")

            if (not isinstance(content_type, str) or not content_type.strip()
                    or "/" not in content_type or "\r" in content_type or "\n" in content_type):
                raise ValueError(
                    f"Every upload for {field} requires a valid content_type")
    return cost


def generate_presigned_files(disposal_id, folder, files):
    """Return transfer-style upload entries using the shared S3 signing helper."""
    uploads = []
    for file_info in files:
        filename = file_info["filename"].strip()
        content_type = file_info["content_type"].strip()
        # This layout routes uploaded files to the disposed block in the
        # existing s3FileUploadLambda consumer.
        key = f"disposals/{disposal_id}/disposal/{folder}/{filename}"
        uploads.append({
            # The shared frontend hook selects compressed images or raw invoices.
            # Disposal documents use its invoices branch; the S3 folder stays documents.
            "type": "images" if folder == "images" else "invoices",
            "filename": filename, "content_type": content_type, "key": key,
            "url": generate_presigned_upload_url(s3, BUCKET_NAME, key, content_type),
        })
    return uploads


def lambda_handler(event, context):
    """Complete an approved disposal at POST /api/disposals/{id}/completed.

    Accept disposalMethod, disposalCost, optional disposalNotes, and optional
    disposalImages/disposalDocuments upload descriptors. Like transfer receipt,
    validate the request, load the record, prepare uploads, and conditionally
    update it. Return the updated record and a flat presigned_urls list on success.

    The disposal contract uses status 'disposed' and a nested disposed block.
    Identity and completion date come from Cognito claims and the backend clock.
    """
    print("event:", json.dumps(event))

    # Browser preflight does not require a body or authenticated user.
    method, headers = handle_request_metadata(
        event, allowed_methods="POST,OPTIONS")
    options_response = handle_options_request(method, headers)

    if options_response:
        return options_response

    try:
        # Require an authenticated subject before accessing disposal data.
        # Never accept disposedBy/Sub from the body as proof of identity.
        identity = get_requestor_identity(event)
        if not identity["requestorSub"]:
            return _response(401, {"message": "Unauthorized"}, headers)

        # Terraform names the path parameter id; disposalId is also accepted
        # for direct invocations. The ID belongs in the path, not the body.
        path = event.get("pathParameters") or {}
        disposal_id = path.get("id") or path.get("disposalId")

        if not isinstance(disposal_id, str) or not disposal_id.strip():
            return _response(400, {"message": "Missing or invalid disposal id"}, headers)

        # The shared parser turns missing/malformed/non-object JSON into 400.
        # Validate every descriptor before any upload URLs are generated.
        data = parse_json_body(event)
        cost = _validate_request(data)
        disposal_item = get_disposal_by_id(disposal_id)

        if not disposal_item:
            return _response(404, {"message": "Disposal not found"}, headers)

        # This endpoint determines the target state; no body status is needed.
        # Reject repeats and requests that have not yet been approved.
        if disposal_item.get("status") != "approved":
            return _response(409, {"message": "Only approved disposals can be completed."}, headers)

        disposal_created = disposal_item["disposalCreated"]
        disposed_by_sub = identity["requestorSub"]
        disposed_by = identity["requestedBy"]
        disposed_date = get_local_now()

        # As with transfer receipt, prepare URLs before committing the update.
        # Signing does not upload files; URLs are returned only after success.
        image_urls = generate_presigned_files(
            disposal_id, "images", data.get("disposalImages", [])
        )
        document_urls = generate_presigned_files(
            disposal_id, "documents", data.get("disposalDocuments", [])
        )

        # Keep completion details nested for the disposal readers/S3 consumer.
        disposed = {
            "disposalId": disposal_item["disposalId"],
            "disposedDate": disposed_date,
            "disposedBy": disposed_by,
            "disposedBySub": disposed_by_sub,
            "disposalMethod": data["disposalMethod"].strip(),
            "disposalCost": cost,
            "disposalNotes": data.get("disposalNotes", ""),
            # The S3 consumer appends metadata after successful uploads.
            "disposalImages": [],
            "disposalDocuments": [],
        }
        # Recheck status atomically: another request may change/delete the item
        # after our query. This also prevents repeat completion wiping uploads.
        result = table_disposals.update_item(
            Key={
                "disposalId": disposal_item["disposalId"],
                "disposalCreated": disposal_created,
            },
            UpdateExpression="""
                SET #status = :status,
                    disposed = :disposed,
                    dateUpdated = :date
            """,
            ConditionExpression=(
                "attribute_exists(disposalId) AND attribute_exists(disposalCreated) "
                "AND #status = :approved"
            ),
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "disposed",
                ":approved": "approved",
                ":disposed": disposed,
                ":date": disposed_date,
            },
            ReturnValues="ALL_NEW",
        )
        return _response(
            200,
            {
                "message": "Disposal completed successfully.",
                "data": result["Attributes"],
                "presigned_urls": image_urls + document_urls,
            },
            headers,
        )

    except ValueError as exc:
        # Invalid client input is actionable by the frontend, not a server error.
        return _response(400, {"message": str(exc)}, headers)

    except ClientError as exc:
        # A failed write condition is a state conflict, not an AWS outage.
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return _response(409, {"message": "Disposal no longer exists or is no longer approved."}, headers)

        print("Error completing disposal:", exc)
        return _response(500, {"message": "AWS service error"}, headers)

    except Exception as exc:
        print("Error completing disposal:", repr(exc))
        return _response(500, {"message": "Internal server error"}, headers)
