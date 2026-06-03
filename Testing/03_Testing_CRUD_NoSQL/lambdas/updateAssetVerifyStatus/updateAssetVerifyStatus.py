import json
import boto3
import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from botocore.config import Config
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client(
    "s3",
    region_name="af-south-1",
    config=Config(
        s3={"addressing_style": "virtual"},
        signature_version="s3v4",
        region_name="af-south-1"
    )
)

TABLE_ASSETS = "crud-nosql-app-assets-table"
TABLE_VERIFICATIONS = "crud-nosql-app-assets-verification-table"

table_assets = dynamodb.Table(TABLE_ASSETS)
table_verifications = dynamodb.Table(TABLE_VERIFICATIONS)

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "POST,PUT,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With",
    "Access-Control-Allow-Credentials": "true"
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

# $  1. Update asset verified by barcode with an dynamodb event stream to eventbridge


def update_assets_table(
    table_assets,
    asset_id: str,
    verification_time: str,
    verifier_name: str,
    position: dict,
):
    # Find asset using AssetIDIndex
    response = table_assets.query(
        IndexName="AssetIDIndex",
        KeyConditionExpression=Key("assetID").eq(asset_id),
        Limit=1,
    )

    items = response.get("Items", [])

    if not items:
        raise Exception(f"Asset not found for assetID {asset_id}")

    asset = items[0]

    table_assets.update_item(
        Key={"id": asset["id"]},
        UpdateExpression="""
            SET verified = :verified,
                last_verified = :time,
                verified_by = :user,
                verified_location = :location
        """,
        ExpressionAttributeValues={
            ":verified": "verified",
            ":time": verification_time,
            ":user": verifier_name,
            ":location": position,
        },
    )

    return {
        "asset_id": asset_id,
        "status": "verified",
    }

# This function are invoked periodically to check the status of the assets and update their status according to the last_verification date


# def check_asset_verification_status():
#     VERIFCATION_STATUS = ["verified", "pending", "overdue", "due soon"]
#     print(VERIFCATION_STATUS)


def normalize_string(value: str | None) -> str:
    return str(value or "").strip().lower()


def lambda_handler(event, context):
    print("event:", event)
    method, HEADERS = handle_request_metadata(event)

    options_response = handle_options_request(method, HEADERS)
    if options_response:
        return options_response

    try:
        if not event.get("body"):
            return _response(400, {"message": "Missing request body"}, HEADERS)

        new_image = event["detail"]["dynamodb"]["NewImage"]

        update_assets_table(
            table_assets=table_assets,
            asset_id=new_image["assetID"]["S"],
            verification_time=new_image["verificationCreated"]["S"],
            verifier_name=new_image["verified_by"]["S"],
            position={
                "latitude": Decimal(
                    new_image["position"]["M"]["latitude"]["N"]
                ),
                "longitude": Decimal(
                    new_image["position"]["M"]["longitude"]["N"]
                ),
            },
        )

    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": "Internal server error"})


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


# Run the lambda locally with the events.json file to test
if __name__ == "__main__":
    with open("event.json") as f:
        event = json.load(f)

    result = lambda_handler(event, None)
    print(json.dumps(result, indent=2))
