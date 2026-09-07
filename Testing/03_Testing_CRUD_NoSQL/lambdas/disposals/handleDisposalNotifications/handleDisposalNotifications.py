import json
import boto3
from botocore.exceptions import ClientError
from decimal import Decimal

from shared_utils.request import require_fields
from shared_utils.to_human_date import get_local_now

dynamodb = boto3.resource("dynamodb")

notifications_table = dynamodb.Table(
    "crud-nosql-app-notifications-table"
)


def lambda_handler(event, context):
    """
    Store all disposal notification types from SQS, preserving producer fields.

    Keep the original recipientSub/notificationCreated key on retries. Duplicate
    delivery cannot overwrite read status. Other failures propagate for retry.
    """

    for record in event["Records"]:
        try:
            notification = json.loads(record["body"], parse_float=Decimal)
            if not isinstance(notification, dict):
                raise ValueError("Notification must be a JSON object")
            required = ("id", "recipientSub", "notificationCreated", "disposalId", "type")
            require_fields(notification, required)
            for field in required:
                if not isinstance(notification[field], str) or not notification[field].strip():
                    raise ValueError(f"Notification {field} must be a non-empty string")

            # Record ingestion time without replacing the producer's sort key.
            notification.setdefault("notificationCreatedAt", get_local_now())

            notifications_table.put_item(
                Item=notification,
                ConditionExpression=(
                    "attribute_not_exists(recipientSub) "
                    "AND attribute_not_exists(notificationCreated)"
                )
            )

            print(
                f"Notification stored: {notification['id']}"
            )

        except ClientError as e:
            error_code = e.response["Error"]["Code"]

            if error_code == "ConditionalCheckFailedException":
                print(
                    f"Notification already exists: "
                    f"{notification.get('id')}"
                )
            else:
                print(f"DynamoDB error: {e}")
                raise

        except Exception as e:
            print(f"Error processing record: {e}")
            raise

    return {
        "statusCode": 200,
        "body": json.dumps("Notifications processed successfully")
    }
