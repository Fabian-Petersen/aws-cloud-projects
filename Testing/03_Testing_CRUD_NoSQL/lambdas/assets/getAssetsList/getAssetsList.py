import json
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Key
from datetime import datetime, timezone, timedelta

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("crud-nosql-app-assets-table")

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",  # or "*"
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}

# $ Dates to be changed from ISO string to human readable date
DATE_TIME_FIELDS = {
    "createdAt",
    "last_verified_at",
}

DATE_FIELDS = {
    "next_verification_due",
}


# $ Change the date format in the database to readible for humans
def to_human_date_time(iso_string: str) -> str:
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


def to_human_date_only(iso_string: str) -> str:
    """
    Convert an ISO 8601 date/timestamp to a date only.

    This does NOT apply timezone conversion because
    date-only fields should not shift by timezone.

    Example:
        2026-08-31
        -> 31 Aug 2026

        2026-08-31T00:00:00Z
        -> 31 Aug 2026
    """
    # Handle a pure date: YYYY-MM-DD
    if "T" not in iso_string:
        dt = datetime.fromisoformat(iso_string)
    else:
        dt = datetime.fromisoformat(
            iso_string.replace("Z", "+00:00")
        )

    return dt.strftime("%d %b %Y")


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

# =========================================================================
# Format all the date fields in the STAGES
# =========================================================================


def format_dates(data):
    if isinstance(data, dict):
        for key, value in data.items():

            if not value:
                continue

            if key in DATE_TIME_FIELDS:
                data[key] = to_human_date_time(value)

            elif key in DATE_FIELDS:
                data[key] = to_human_date_only(value)

            else:
                format_dates(value)

    elif isinstance(data, list):
        for item in data:
            format_dates(item)


def lambda_handler(event, context):
    print("event:", json.dumps(event))
    # Grab the Origin header from the incoming request
    headers = event.get("headers") or {}
    origin = headers.get("origin") or headers.get("Origin") or ""

    allowedOrigins = [
        'https://www.crud-nosql.app.fabian-portfolio.net',
        'https://crud-nosql.app.fabian-portfolio.net',
        'http://localhost:5173'
    ]

    # Only allow known origins
    allowedOrigin = origin if origin in allowedOrigins else ""

    HEADERS = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": allowedOrigin,
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Credentials": "true"
    }

    method = (
        event.get("httpMethod")
        or event.get("requestContext", {}).get("http", {}).get("method")
    )

    if method == "OPTIONS":
        print("OPTIONS request...")
        return _response(200, {"message": "Success"}, HEADERS)

    try:
        response = table.scan()
        items = response.get("Items", [])
        for item in items:
            format_dates(item)

        print("response:", json.dumps(response.get(
            "Items", []), default=decimal_serializer))

        return _response(200, response.get("Items", []), HEADERS)

    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": "Internal server error"})


def _response(status_code, body, headers):
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
