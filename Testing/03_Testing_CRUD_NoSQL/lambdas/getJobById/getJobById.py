"""
This function retrieves a specific maintenance job by its ID and status. It supports both pending/approved jobs from the request table and actioned jobs from the action table. The function validates the input parameters, formats dates for human readability, and generates presigned URLs for any associated images stored in S3. CORS headers are included to allow cross-origin requests from the frontend application. The function also includes robust error handling for missing parameters, invalid status values, and database retrieval issues.
"""

import json
import os
import boto3
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from boto3.dynamodb.conditions import Key
from botocore.config import Config

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("crud-nosql-app-maintenance-request-table")

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
VALID_STATUSES = {"pending", "in progress", "complete", "rejected"}

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


def add_presigned_urls(item: dict) -> dict:
    images = item.get("images", [])
    if not isinstance(images, list):
        return item
    new_images = []
    for img in images:
        if not isinstance(img, dict):
            new_images.append(img)
            continue
        bucket = img.get("bucket")
        key = img.get("key")
        new_img = {
            "key": key,
            "filename": img.get("filename") or (key.split("/")[-1] if key else None),
            "url": None
        }
        if bucket and key:
            try:
                new_img["url"] = s3.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={"Bucket": bucket, "Key": key},
                    ExpiresIn=PRESIGN_EXPIRES_SECONDS,
                )
            except Exception as e:
                print("Presign error:", e)
        new_images.append(new_img)
    item["images"] = new_images
    return item


def get_request_job(job_id: str, status: str, headers) -> dict:
    result = table.query(
        KeyConditionExpression=Key("id").eq(job_id)
    )
    items = result.get("Items", [])
    if not items:
        return _response(404, {"message": "Job not found"}, headers)

    item = items[0]

    if item.get("status") != status:
        return _response(404, {"message": "Job not found"}, headers)

    if "jobCreated" in item:
        item["jobCreated"] = to_human_date(item["jobCreated"])

    return _response(200, add_presigned_urls(item), headers)


def lambda_handler(event, context):
    # CORS
    method, HEADERS = handle_request_metadata(event)

    options_response = handle_options_request(method, HEADERS)
    if options_response:
        return options_response

    print("event:", event)

    try:
        job_id = event.get("pathParameters", {}).get("id")
        status = (event.get("queryStringParameters") or {}).get("status")

        if not job_id:
            return _response(400, {"message": "Missing job id"}, HEADERS)

        if not status or status not in VALID_STATUSES:
            return _response(400, {"message": f"Invalid or missing status. Must be one of: {', '.join(VALID_STATUSES)}"}, HEADERS)

        return get_request_job(job_id, status, HEADERS)

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
