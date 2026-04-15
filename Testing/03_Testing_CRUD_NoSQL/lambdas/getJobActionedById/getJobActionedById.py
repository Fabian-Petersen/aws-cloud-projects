import json
import boto3
from datetime import datetime, timezone, timedelta

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("crud-nosql-app-maintenance-action-table")

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With"
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

def lambda_handler(event, context):
    try:
        # Path param from API Gateway
        request_id = event.get("pathParameters", {}).get("id")

        if not request_id:
            return _response(400, {"message": "Missing request id"})

        # Use GetItem (fast, exact match)
        result = table.get_item(
            Key={"id": request_id}
        )

        item = result.get("Item")

        if not item:
            return _response(404, {"message": "Maintenance request not found"})

        for field in ["createdAt", "start_time", "end_time"]:
            if field in item:
                item[field] = to_human_date(item[field])

        return _response(200, item)

    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": "Internal server error"})

def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": HEADERS,
        "body": json.dumps(body),
    }