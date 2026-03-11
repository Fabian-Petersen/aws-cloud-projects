import json
import boto3
from datetime import datetime
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("crud-nosql-app-maintenance-request-table")

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Credentials": "true"
}

def to_human_date(iso_string: str) -> str:
    dt = datetime.fromisoformat(iso_string)
    return dt.strftime("%d %b %Y, %H:%M")

def lambda_handler(event, context):
    # print("Event:", event)
    try:
        request_id = event.get("pathParameters", {}).get("id")
        print(f"Request ID: {request_id}")

        if not request_id:
            return _response(400, {"message": "Missing request id"})

        result = table.query(
            KeyConditionExpression=Key("id").eq(request_id)
        )

        # print("result:", result)

        items = result.get("Items", [])

        if not items:
            return _response(404, {"message": "Maintenance request not found"})

        item = items[0]

        if "jobCreated" in item:
            item["jobCreated"] = to_human_date(item["jobCreated"])

        return _response(200, item)

    except Exception as exc:
        print("Error:", str(exc))
        return _response(500, {"message": "Internal server error"})

def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": HEADERS,
        "body": json.dumps(body),
    }