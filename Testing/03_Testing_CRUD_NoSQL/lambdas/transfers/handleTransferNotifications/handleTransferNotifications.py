import json
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timezone, timedelta

dynamodb = boto3.resource("dynamodb")

notifications_table = dynamodb.Table(
    "crud-nosql-app-notifications-table"
)


def lambda_handler(event, context):
    print("event:", event)
    """
    Processes notification messages from SQS and stores them in DynamoDB.
    """

    for record in event["Records"]:
        try:
            notification = json.loads(record["body"])

            # Get the current time for the update
            sast = timezone(timedelta(hours=2))
            now = datetime.now(sast).isoformat()

            # Timestamp when the notification record is created
            notification["notificationCreatedAt"] = now

            notifications_table.put_item(
                Item=notification,
                ConditionExpression="attribute_not_exists(id)"
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
