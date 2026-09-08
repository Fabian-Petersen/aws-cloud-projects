import json
import os
import uuid
import boto3
from boto3.dynamodb.types import TypeDeserializer
from boto3.dynamodb.conditions import Key
from datetime import datetime, timezone, timedelta

sqs = boto3.client("sqs")
ssm = boto3.client("ssm")

deserializer = TypeDeserializer()
dynamodb = boto3.resource("dynamodb")

NOTIFICATION_QUEUE_URL = os.getenv("NOTIFICATION_QUEUE_URL",
                                   "/crud-nosql/sqs")


def get_sqs_url():
    """Fetch the queue URL from the SSM Parameter Store"""
    response = ssm.get_parameter(Name=NOTIFICATION_QUEUE_URL)
    return response["Parameter"]["Value"]


users_table = dynamodb.Table("crud-nosql-app-users-table")


def deserialize(image):
    """Convert DynamoDB Stream image to normal Python dict."""
    return {k: deserializer.deserialize(v) for k, v in image.items()}


# ---------------------------------------------------------------------------- #
#                       PUBLISH NOTIFICATION -> SQS QUEUE                      #
# ---------------------------------------------------------------------------- #


def publish_notification(notification: dict) -> None:
    """
    Publishes a single notification to the notifications SQS queue, which
    is picked up by the handleNotifications Lambda and written to the
    notifications table.

    Args:
        notification: The notification payload built by build_notification().

    Returns:
        None

    Example:
        >>> publish_notification({"notificationId": "...", "recipientSub": "mgr-sub", ...})
    """
    sqs_url = get_sqs_url()
    print("sqs_url:", sqs_url)
    sqs.send_message(
        QueueUrl=sqs_url,
        MessageBody=json.dumps(notification)
    )


def lambda_handler(event, context):
    print("event:", json.dumps(event))

    for record in event.get("Records", []):

        body = json.loads(record["body"])
        detail = body["detail"]
        dynamodb = detail["dynamodb"]

        new_image = deserialize(dynamodb["NewImage"])
        old_image = deserialize(dynamodb.get("OldImage", {}))

        # Only process approval event
        if (
            old_image.get("status") != "pending"
            or new_image.get("status") != "approved"
        ):
            continue

        disposal_id = new_image["id"]

        # requestor_name = new_image["requestor_name"]
        requestor_sub = new_image["requestor_sub"]

        # approver_name = new_image["approvedBy"]
        # approver_sub = new_image["approvedBySub"]

        location = new_image["location"]
        approved_date = new_image["approvedDate"]

        ttl = int(
            (datetime.now(timezone.utc) + timedelta(days=90)).timestamp()
        )


# ---------------------------------------------------------------------------- #
#                          Notification for Requestor                          #
# ---------------------------------------------------------------------------- #

        requestor_notification = {
            "id": str(uuid.uuid4()),
            "recipientSub": requestor_sub,
            "disposalId": disposal_id,
            "notificationCreated": approved_date,
            "status": "UNREAD",
            "priority": "NORMAL",
            "type": "DISPOSAL_APPROVED",
            "title": "Disposal Approved",
            "message": (
                f"Your disposal request from {location} to has been approved."
            ),
            "channels": [
                "IN_APP",
                "EMAIL"
            ],
            "ttl": ttl
        }

        publish_notification(requestor_notification)

    return {
        "statusCode": 200,
        "body": json.dumps("Notifications queued.")
    }
