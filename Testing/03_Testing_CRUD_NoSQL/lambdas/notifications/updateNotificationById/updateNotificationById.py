import json
import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("crud-nosql-app-notifications-table")

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "PUT,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With",
    "Access-Control-Allow-Credentials": "true"
}


def lambda_handler(event, context):
    print("event", event)
    try:
        body = json.loads(event.get("body", "{}"))
        if not body:
            return _response(400, {"message": "Request body is required"})

        claims = (
            event.get("requestContext", {})
            .get("authorizer", {})
            .get("claims", {})
        )

        recipientSub = claims.get("sub", "")
        notification_created = body.get("notificationCreated", "").strip()

        # Update the item
        table.update_item(
            Key={
                "recipientSub": recipientSub,
                "notificationCreated": notification_created,
            },
            UpdateExpression="SET #status = :status",
            ExpressionAttributeNames={
                "#status": "status",
            },
            ExpressionAttributeValues={
                ":status": "ARCHIVED",
            },
            ConditionExpression="attribute_exists(recipientSub) AND attribute_exists(notificationCreated)",
            ReturnValues="ALL_NEW",
        )
        return _response(200, {"message": "Notification updated successfully"})

    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": "Internal server error"})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": HEADERS,
        "body": json.dumps(body),
    }
