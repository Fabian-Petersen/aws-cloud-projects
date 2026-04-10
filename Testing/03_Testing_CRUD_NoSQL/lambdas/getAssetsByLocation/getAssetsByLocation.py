"""
This Lambda function returns all assets filtered by the authenticated user's location.
The user's location is retrieved from the users table using their Cognito `sub`.
"""

import json
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Key
from datetime import datetime, timezone, timedelta

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("crud-nosql-app-assets-table")
table_users = dynamodb.Table("crud-nosql-app-users-table")

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


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


def get_user_location(user_sub: str) -> str:
    """
    Retrieve the user's location from the users table using their Cognito sub.

    Args:
        user_sub (str): Cognito user unique identifier.

    Returns:
        str: The user's assigned location.

    Raises:
        Exception: If the user or location attribute is not found.
    """
    response = table_users.get_item(
        Key={"id": user_sub}
    )

    user = response.get("Item")
    if not user or "location" not in user:
        raise Exception("User location not found")

    return user["location"]


def get_assets_by_location(location: str):
    """
    Query the assets table for all assets belonging to a specific location.

    Uses a DynamoDB Global Secondary Index (GSI) on the 'location' attribute.

    Args:
        location (str): Location used to filter assets.

    Returns:
        list: List of assets matching the given location with formatted dates.
    """
    response = table.query(
        IndexName="LocationIndex",
        KeyConditionExpression=Key("location").eq(location)
    )

    items = response.get("Items", [])

    for item in items:
        if "createdAt" in item:
            item["createdAt"] = to_human_date(item["createdAt"])

    return items


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


def lambda_handler(event, context):
    """
    AWS Lambda entry point.

    Workflow:
        1. Process request metadata (method + headers)
        2. Handle preflight OPTIONS request
        3. Extract authenticated user from request context
        4. Retrieve user location from users table
        5. Query assets filtered by location
        6. Return filtered assets as JSON response

    Args:
        event (dict): Lambda event payload.
        context (object): Lambda runtime context.

    Returns:
        dict: API Gateway compatible HTTP response.
    """
    method, HEADERS = handle_request_metadata(event)

    options_response = handle_options_request(method, HEADERS)
    if options_response:
        return options_response

    try:
        claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
        user_sub = claims.get("sub")

        if not user_sub:
            return _response(401, {"message": "Unauthorized"}, HEADERS)

        location = get_user_location(user_sub)
        assets = get_assets_by_location(location)

        return _response(200, assets, HEADERS)

    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": str(exc)}, HEADERS)


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


# --- Local testing ---
if __name__ == "__main__":
    """
    Local test runner for simulating Lambda execution.

    Loads an event from 'event.json' and prints the formatted response.
    """
    with open("event.json") as f:
        event = json.load(f)

    result = lambda_handler(event, None)
    print(json.dumps(result, indent=2))