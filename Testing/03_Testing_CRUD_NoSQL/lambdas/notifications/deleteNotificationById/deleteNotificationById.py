import json
import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

TABLE_NAME = "crud-nosql-app-notifications-table"

table = dynamodb.Table(TABLE_NAME)

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "DELETE,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With",
    "Access-Control-Allow-Credentials": "true"
}


def normalize_string(value: str | None) -> str:
    return str(value or "").strip().lower()


def lambda_handler(event, context):
    print("event:", event)
    try:
        if not event.get("body"):
            return _response(400, {"message": "Missing request body"})

        data = json.loads(event["body"])

        # $ Validate required fields (assetID and description is not required)
        required_fields = ["notificationCreated"]
        for field in required_fields:
            if not data.get(field):
                return _response(400, {"message": f"Missing or empty field: {field}"})

        claims = (
            event.get("requestContext", {})
            .get("authorizer", {})
            .get("claims", {})
        )

        recipientSub = claims.get("sub", "")
        notification_created = data.get("notificationCreated").strip()

        # $ Get transfer_id from the pathParameters in the path
        id = event.get("pathParameters", {}).get("id")

        # $ Get the item from the table
        response = table.get_item(
            Key={
                "recipientSub": recipientSub,
                "notificationCreated": notification_created,
            }
        )

        item = response.get("Item")
        if not item:
            return _response(404, {"message": "Notification not found"})

        if item["id"] != id:
            return _response(400, {"message": "Notification ID mismatch"})

        # 3. Delete DynamoDB item
        table.delete_item(
            Key={
                "recipientSub": recipientSub,
                "notificationCreated": notification_created
            }
        )

        return _response(200, {"message": "Notification deleted successfully"})

    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": "Internal server error"})


# ----------------------------
# Response helper
# ----------------------------
def _response(status_code, body):
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
        "headers": HEADERS,
        "body": json.dumps(body),
    }
