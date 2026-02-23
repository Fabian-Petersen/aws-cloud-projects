import json
import boto3
from datetime import datetime

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("crud-nosql-app-assets-table")

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With",
    "Access-Control-Allow-Credentials": "true"
}

def to_human_date(iso_string: str) -> str:
    dt = datetime.fromisoformat(iso_string)
    return dt.strftime("%d %b %Y, %H:%M")

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
            return _response(404, {"message": "Asset not found"})

        if "createdAt" in item:
            item["createdAt"] = to_human_date(item["createdAt"])

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