"""
This function retrieves a specific maintenance job by its ID and status. 
It supports both pending/approved jobs from the request table and actioned jobs from the action table. 
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
request_table = dynamodb.Table("crud-nosql-app-maintenance-request-table")
action_table = dynamodb.Table("crud-nosql-app-maintenance-action-table")

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
    # Get the jobCreated ID for the SK
    # =========================================================================


def get_job_created_by_id(table, request_id: str) -> str:
    # jobCreated is the SK for the table
    response = table.query(
        KeyConditionExpression=Key("id").eq(request_id)
    )
    items = response.get("Items", [])
    if not items:
        raise ValueError("Item not found")
    # If only one item per id, take the first
    return items[0]["jobCreated"]

    # =========================================================================
    # Get the Action ID from the item in the request table
    # =========================================================================


def get_actionID(request_id: str) -> str | None:
    response = request_table.query(
        KeyConditionExpression=Key("id").eq(request_id)
    )

    items = response.get("Items", [])

    if not items:
        return None

    return items[0].get("action_id")

    # =========================================================================
    # Get jobs requested with status (pending, in progress, rejected, complete)
    # =========================================================================


def get_request_job(request_id: str, status: str, headers) -> dict:
    """
    The frontend send the request_id for the pending, in progress, rejected jobs
    """
    # $ 1. Base job (always from request table status = pending, rejected or in progress)
    response = request_table.query(
        KeyConditionExpression=Key("id").eq(request_id)
    )

    items = response.get("Items", [])
    if not items:
        return _response(404, {"message": "Job not found"}, headers)

    item = items[0]

    if item.get("status") != status:
        return _response(404, {"message": "Job not found"}, headers)

    if "jobCreated" in item:
        item["jobCreated"] = to_human_date(item["jobCreated"])

    # $ 2. If NOT complete → return base only
    if status != "complete":
        return _response(
            200,
            add_presigned_urls(item),
            headers
        )


def get_complete_job(action_id: str, headers) -> dict:
    """
    Frontend sends action_id for complete jobs.
    1. Query action_table to get request_id
    2. Query request_table with request_id to get base job
    3. Merge and return
    """

    # Step 1 — get request_id from action_table
    action_result = action_table.query(
        KeyConditionExpression=Key("id").eq(action_id)
    )
    action_items = action_result.get("Items", [])

    if not action_items:
        return _response(200, {"error": "NOT_FOUND", "message": "Completed job not found"}, headers)

    action_data = action_items[0]
    request_id = action_data.get("request_id")

    if not request_id:
        return _response(200, {"error": "NOT_FOUND", "message": "No request_id on action record"}, headers)

    # Step 2 — get base job from request_table using request_id
    req_result = request_table.query(
        KeyConditionExpression=Key("id").eq(request_id)
    )
    req_items = req_result.get("Items", [])

    if not req_items:
        return _response(200, {"error": "NOT_FOUND", "message": "Base job not found"}, headers)

    base_item = req_items[0]

    if "jobCreated" in base_item:
        base_item["jobCreated"] = to_human_date(base_item["jobCreated"])

    # Remove signature before returning to frontend
    sanitized_action_data = {
        k: v for k, v in action_data.items() if k != "signature"
    }

    # Step 3 — merge and return
    merged = {
        **base_item,
        "action_data": sanitized_action_data,
    }

    return _response(200, add_presigned_urls(merged), headers)


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

        if status == "complete":
            # -> job_id is action_id here
            return get_complete_job(job_id, HEADERS)
        else:
            # -> job_id is request_id here
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
