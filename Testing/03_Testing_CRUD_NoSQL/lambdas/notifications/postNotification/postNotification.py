import json
import boto3
from datetime import datetime, timezone, timedelta
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("crud-nosql-app-notifications-table")

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Credentials": "true"
}


def get_local_now():
    tz = timezone(timedelta(hours=2))
    return datetime.now(tz).isoformat()


# Fields that clients are allowed to update
ALLOWED_FIELDS = {
    "status",
    # "archived",
    # "starred",
    # "deleted",
}


def lambda_handler(event, context):
    # print("event:", event.get("body"))
    try:
        if not event.get("body"):
            return _response(400, {"message": "Missing request body"})

        # $ Get the user information from the authoriser token.
        data = json.loads(event["body"])

        # $ Validate required fields
        required_fields = ["recipientSub", "notificationCreated", "status",
                           "id"]
        for field in required_fields:
            if not data.get(field):
                return _response(400, {"message": f"Missing or empty field: {field}"})

        recipient_sub = data.get("recipientSub")
        notification_created = data.get("notificationCreated")
        notification_id = data.get("id")

        if not recipient_sub:
            return _response(400, {"message": "sub is required"})

        if not notification_created:
            return _response(400, {"message": "notificationCreated is required"})

        if not notification_id:
            return _response(400, {"message": "notificationId is required"})

        update_expression = []
        expression_names = {"#status": "status"}
        expression_values = {}

        for field in ALLOWED_FIELDS:
            if field in data:
                update_expression.append(f"#{field} = :{field}")
                expression_names[f"#{field}"] = field
                expression_values[f":{field}"] = data[field]

        if data.get("status") == "READ":
            update_expression.append("#dateRead = :dateRead")
            expression_names["#dateRead"] = "dateRead"
            expression_values[":dateRead"] = get_local_now()

        if not update_expression:
            return _response(
                400,
                {"message": "No valid fields supplied for update"},
            )

        # Values used by the condition expression
        expression_values[":id"] = notification_id
        expression_values[":unread"] = "UNREAD"

        result = table.update_item(
            Key={
                "recipientSub": recipient_sub,
                "notificationCreated": notification_created,
            },
            UpdateExpression="SET " + ", ".join(update_expression),
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values,
            ConditionExpression="""
            attribute_exists(recipientSub)
            AND attribute_exists(notificationCreated)
            AND id = :id
            AND #status = :unread
            """,
            ReturnValues="ALL_NEW",
        )

        print("result:", result)

        return _response(200, {"message": "Notification updated successfully", "notification": result["Attributes"],
                               },
                         )

    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return _response(404, {"message": "Notification not found"},
                             )

        return _response(500, {"message": "DynamoDB error", "error": str(e), },
                         )

    except Exception as e:
        return _response(500, {"message": "Internal server error", "error": str(e),
                               },
                         )


def _response(status_code, data):
    return {
        "statusCode": status_code,
        "headers": HEADERS,
        "body": json.dumps(data),
    }
