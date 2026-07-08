"""
This function retrieves a specific transfer request by its ID and status. 
It supports both pending/approved transfers from the assets transfer table. 
The function validates the input parameters, formats dates for human readability, and generates presigned URLs for any associated images stored in S3. 
CORS headers are included to allow cross-origin requests from the frontend application. 
The function also includes robust error handling for missing parameters, invalid status values, and database retrieval issues.
"""

import json
import os
import boto3
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from boto3.dynamodb.conditions import Key
from botocore.config import Config

dynamodb = boto3.resource("dynamodb")
transfer_table = dynamodb.Table("crud-nosql-app-assets-transfer-table")

s3 = boto3.client(
    "s3",
    region_name="af-south-1",
    config=Config(
        s3={"addressing_style": "virtual"},
        signature_version="s3v4",
        region_name="af-south-1"
    )
)

PRESIGN_EXPIRES_SECONDS = int(os.getenv("PRESIGN_EXPIRES_SECONDS", "900"))
VALID_STATUSES = {"pending", "in-transit",
                  "receipted", "cancelled", "rejected", "approved"}

# $ STAGES: Used to build the response object for the frontend
STAGES = {
    "request": [
        "requested_by",
        "requestor_name",
        "requestor_sub",
        "assetID",
        "area",
        "images",
        "equipment",
        "description",
        "transferReason",
        "locationFrom",
        "locationTo",
        "expectedDate",
    ],
    "approved": [
        "approvalId",
        "dateApproved",
        "approvedBy"
        "approvedBySub",
        "approvalReminderCount",
    ],
    "inTransit": [
        "transitId",
        "dateCreated",
        "inTransitSub",
        "transportType",
        "transportName",
        "transportDate",
        "trackingNumber",
        "transportNotes",
        "transportCost",
        "images",
        "invoices",
    ],
    "receipt": [
        "receiptId",
        "dateReceived",
        "receivedBySub",
        "receiptStatus",
        "condition",
        "damageDetails",
        "receiptImages",
        "deliveryNote",
    ],
    "cancelled": [
        "dateCancelled",
        "cancelledBySub",
        "cancelReason",
        "cancelStatus",
    ],
}

# $ Dates to be changed from ISO string to human readable date
DATE_FIELDS = {
    "transferCreated",
    "expectedDate",
    "dateApproved",
    "dateCreated",
    "transportDate",
    "dateReceived",
    "dateCancelled",
}

# ----------------------------
# Decimal serializer for DynamoDB types in JSON responses
# ----------------------------


def decimal_serializer(obj):
    """
    Custom JSON serializer for handling DynamoDB Decimal types.

    Args:
        obj: Object to serialize.

    Returns:
        int | float: Converted numeric value.

    Raises:
        TypeError: If object type is not supported.
    """
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    raise TypeError

# ----------------------------
# Date formatting in SAST for human readability
# ----------------------------


def to_human_date(iso_string: str) -> str:
    """
    Convert an ISO 8601 timestamp string to a human-readable date in SAST.

    Args:
        iso_string (str): ISO formatted datetime string (e.g., "2024-01-01T12:00:00Z").

    Returns:
        str: Formatted date string (e.g., "01 Jan 2024, 14:00").
    """
    SAST = timezone(timedelta(hours=2))
    dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    return dt.astimezone(SAST).strftime("%d %b %Y, %H:%M")


def handle_request_metadata(event):
    """
    Extract HTTP method and construct CORS headers based on request origin.

    Args:
        event (dict): Lambda event payload.

    Returns:
        tuple:
            method (str): HTTP method (GET, POST, OPTIONS, etc.)
            response_headers (dict): CORS-enabled response headers.
    """
    headers = event.get("headers") or {}
    origin = headers.get("origin") or headers.get("Origin") or ""

    allowed_origins = [
        "https://www.crud-nosql.app.fabian-portfolio.net",
        "https://crud-nosql.app.fabian-portfolio.net",
        "http://localhost:5173",
        "http://localhost:8080"
    ]

    allowed_origin = origin if origin in allowed_origins else ""

    response_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": allowed_origin,
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Credentials": "true",
    }

    method = (
        event.get("httpMethod")
        or event.get("requestContext", {}).get("http", {}).get("method")
    )

    return method, response_headers


def handle_options_request(method, headers):
    """
    Handle CORS preflight (OPTIONS) requests.

    Args:
        method (str): HTTP method.
        headers (dict): Response headers.

    Returns:
        dict | None: HTTP response if OPTIONS request, otherwise None.
    """
    if method == "OPTIONS":
        return _response(200, {"message": "Success"}, headers)
    return None


def add_presigned_urls(data):
    """
    Recursively traverse dictionaries/lists and add presigned URLs
    to any object containing an S3 bucket/key pair.
    """

    # Handle dictionaries
    if isinstance(data, dict):

        # Detect S3 file object
        if "bucket" in data and "key" in data:
            bucket = data.get("bucket")
            key = data.get("key")

            new_data = {
                "key": key,
                "filename": data.get("filename")
                or (key.split("/")[-1] if key else None),
                "url": None,
            }

            if bucket and key:
                try:
                    new_data["url"] = s3.generate_presigned_url(
                        ClientMethod="get_object",
                        Params={
                            "Bucket": bucket,
                            "Key": key,
                        },
                        ExpiresIn=PRESIGN_EXPIRES_SECONDS,
                    )
                except Exception as e:
                    print("Presign error:", e)

            return new_data

        # Recursively process nested dict values
        return {
            k: add_presigned_urls(v)
            for k, v in data.items()
        }

    # Handle lists
    if isinstance(data, list):
        return [add_presigned_urls(item) for item in data]

    # Return primitive values unchanged
    return data


# =========================================================================
# Format all the date fields in the STAGES
# =========================================================================

def format_dates(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if key in DATE_FIELDS and value:
                data[key] = to_human_date(value)
            else:
                format_dates(value)

    elif isinstance(data, list):
        for item in data:
            format_dates(item)

# =========================================================================
# Build the response object
# =========================================================================


def build_transfer_response(item):
    response = {
        "id": item["id"],
        "assetID": item["assetID"],
        "status": item["status"],
        "transferCreated": item["transferCreated"],
    }

    for stage, fields in STAGES.items():
        data = {}

        for field in fields:
            if field in item:
                data[field] = item[field]

        response[stage] = data or None

    return response

# =========================================================================
# Get transfer by request ID (GSI: id)
# =========================================================================


def get_transfer_by_id(table, request_id: str) -> dict:
    response = table.query(
        IndexName="IdIndex",
        KeyConditionExpression=Key("id").eq(request_id)
    )

    items = response.get("Items", [])

    if not items:
        raise ValueError("Transfer request not found")

    return items[0]

# =========================================================================
# Get transfer request by status
# =========================================================================


def get_transfer_request(request_id: str, status: str, headers) -> dict:
    """
    The frontend sends the request_id.
    """

    try:
        item = get_transfer_by_id(transfer_table, request_id)
        response = build_transfer_response(item)
        format_dates(response)
        response = add_presigned_urls(response)

    except ValueError:
        return _response(
            404,
            {"message": "Transfer Request not found"},
            headers,
        )

    if item.get("status") != status:
        return _response(
            404,
            {"message": "Transfer Request not found"},
            headers,
        )

    return _response(
        200,
        response,
        headers,
    )


def lambda_handler(event, context):
    # CORS
    method, HEADERS = handle_request_metadata(event)

    options_response = handle_options_request(method, HEADERS)
    if options_response:
        return options_response

    print("event:", event)

    try:
        request_id = event.get("pathParameters", {}).get("id")
        status = (event.get("queryStringParameters") or {}).get("status")

        if not request_id:
            return _response(400, {"message": "Missing request id"}, HEADERS)

        if not status or status not in VALID_STATUSES:
            return _response(400, {"message": f"Invalid or missing status. Must be one of: {', '.join(VALID_STATUSES)}"}, HEADERS)

        return get_transfer_request(request_id, status, HEADERS)

    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": "Internal server error"}, HEADERS)

# ----------------------------
# Response helper
# ----------------------------


def _response(status_code, body, headers):
    """
    Construct a standard API Gateway HTTP response.

    Args:
        status_code (int): HTTP status code.
        body (dict | list): Response payload.
        headers (dict): HTTP headers.

    Returns:
        dict: Formatted response object.
    """
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body, default=decimal_serializer),
    }
