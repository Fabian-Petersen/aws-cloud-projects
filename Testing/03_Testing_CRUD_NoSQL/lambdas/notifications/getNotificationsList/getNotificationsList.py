"""
This function returns all the user notifications from the notifications table. CORS headers are dynamically set based on the request origin, and dates are formatted for human readability in SAST. The function handles OPTIONS requests for CORS preflight and includes robust error handling for missing user information or database issues.

"""

import json
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, timezone, timedelta

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("crud-nosql-app-notifications-table")

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
# Cognito groups parser for flexible group claim formats
# ----------------------------


def parse_groups(groups_claim):
    if not groups_claim:
        return []

    if isinstance(groups_claim, list):
        return [str(group).lower() for group in groups_claim]

    if isinstance(groups_claim, str):
        try:
            parsed = json.loads(groups_claim)
            if isinstance(parsed, list):
                return [str(group).lower() for group in parsed]
        except Exception:
            pass

        return [group.strip().lower() for group in groups_claim.split(",")]

    return []

# ----------------------------
# Construct Headers
# ----------------------------


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


# ----------------------------
# Construct Options
# ----------------------------

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


# =========================================================================
# Format all the date fields
# =========================================================================

DATE_FIELDS = {
    "transferCreated",
    "notificationCreatedDisplay",
    "dateRead",
}


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


# ----------------------------
# GSI query (status-based)
# ----------------------------
def query_by_user(recipient_sub):
    items = []
    # Notifications that were READ already within the last 3 days will be send to FE
    cutoff = datetime.now(timezone.utc) - timedelta(days=3)

    response = table.query(
        KeyConditionExpression=Key("recipientSub").eq(recipient_sub),
        ScanIndexForward=False,
    )

    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = table.query(
            KeyConditionExpression=Key("recipientSub").eq(recipient_sub),
            ScanIndexForward=False,
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )

        items.extend(response.get("Items", []))

    filtered = []

    for item in items:
        status = item.get("status")

        if status == "UNREAD":
            filtered.append(item)

        elif status == "READ":
            created = datetime.fromisoformat(item["notificationCreated"])
            if created >= cutoff:
                filtered.append(item)
# sort the items such that UNREAD items always on top in order
    return filtered.sort(key=lambda item: item["status"] == "READ")
# ----------------------------
# Scan fallback (no filters)
# ----------------------------


def scan_all():
    items = []
    response = table.scan()
    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = table.scan(
            ExclusiveStartKey=response["LastEvaluatedKey"]
        )
        items.extend(response.get("Items", []))

    return items

# ----------------------------
# Lambda handler
# ----------------------------


def lambda_handler(event, context):
    print("event:", event)

    # Query params
    userId = event.get("pathParameters") or {}

    # Auth claims
    claims = event.get("requestContext", {}).get(
        "authorizer", {}).get("claims", {})
    user_sub = claims.get("sub")

    # CORS
    method, HEADERS = handle_request_metadata(event)

    options_response = handle_options_request(method, HEADERS)
    if options_response:
        return options_response

    try:

        # ----------------------------
        # DATA FETCH LOGIC
        # ----------------------------

        # Non-admin users only see their own jobs
        if not user_sub:
            return _response(403, {"message": "User sub not found"}, HEADERS)

        items = query_by_user(user_sub)

        # ----------------------------
        # Build response
        # ----------------------------

        response = []

        for item in items:
            # Preserve the original sort key for the notifications update from frontend
            item["notificationCreatedDisplay"] = item.get(
                "notificationCreated")
            format_dates(item)
            response.append(item)

        return _response(200, response, HEADERS)

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
