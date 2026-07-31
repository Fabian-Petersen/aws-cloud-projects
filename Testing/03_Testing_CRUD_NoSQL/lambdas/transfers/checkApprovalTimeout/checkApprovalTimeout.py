import json
import os
import uuid
from datetime import datetime, timezone, timedelta

import boto3

sqs = boto3.client("sqs")
ssm = boto3.client("ssm")

# dynamodb = boto3.resource("dynamodb")

# users_table = dynamodb.Table("crud-nosql-app-users-table")
# assets_table = dynamodb.Table("crud-nosql-app-assets-table")

NOTIFICATION_QUEUE_URL = os.getenv("NOTIFICATION_QUEUE_URL",
                                   "/crud-nosql/sqs")


def get_ssm_parameter_value(name: str) -> str:
    """Fetch the parameter value from the SSM Parameter Store"""
    response = ssm.get_parameter(Name=name)
    return response["Parameter"]["Value"]


# ---------------------------------------------------------------------------- #
#                       BUILD NOTIFICATION                                     #
# ---------------------------------------------------------------------------- #


def build_notification(recipient: dict, transfer: dict) -> dict:
    """
    Builds a single notification payload for one recipient of a transfer
    approval request.

    Args:
        recipient: A dict with "sub" and "email" keys, as returned by
            get_recipients().
        transfer: The raw DynamoDB Streams NewImage for the transfer
            record (attribute-map format, e.g. {"assetID": {"S": "..."}}).

    Returns:
        dict: A notification record ready to be JSON-serialized and
        published to the notifications queue.

    Example:
        >>> build_notification(
        ...     {"sub": "mgr-sub", "email": "mgr@company.com"},
        ...     {"assetID": {"S": "abc-123"}, "id": {"S": "transfer-456"}},
        ... )
        {"notificationId": "...", "recipientSub": "mgr-sub", ...}
    """

    asset_id = transfer["assetID"]["S"]
    transfer_id = transfer["id"]["S"]
    location_from = transfer["locationFrom"]["S"]

    # Get the current time for the update
    sast = timezone(timedelta(hours=2))
    now = datetime.now(sast).isoformat()

    ttl = int(
        (datetime.now(timezone.utc) + timedelta(days=90)).timestamp()
    )

    return {
        "notificationCreated": now,
        "id": str(uuid.uuid4()),

        "recipientSub": recipient["sub"],
        "recipientEmail": recipient["email"],

        "type": "APPROVAL_REMINDER",
        "title": "Reminder: Asset Transfer Request",
        "message": f"Reminder to approve the transfer of asset {asset_id}.",
        "location": location_from,

        "assetId": asset_id,
        "transferId": transfer_id,

        "status": "UNREAD",
        "priority": "NORMAL",

        "channels": [
            "IN_APP",
            "EMAIL"
        ],

        "ttl": ttl
    }

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
    sqs_url = get_ssm_parameter_value(NOTIFICATION_QUEUE_URL)
    # print("sqs_url:", sqs_url)
    sqs.send_message(
        QueueUrl=sqs_url,
        MessageBody=json.dumps(notification)
    )


# ---------------------------------------------------------------------------- #
#                       LAMBDA - HANDLER                                       #
# ---------------------------------------------------------------------------- #


def lambda_handler(event, context):
    print("Reminder event:", event)

    if event.get("type") != "APPROVAL_REMINDER":
        raise ValueError("Unexpected event type")

    transfer = event["transfer"]
    recipients = event["recipients"]

    for recipient in recipients:
        notification = build_notification(recipient, transfer)
        publish_notification(notification)

    return {
        "statusCode": 200,
        "body": json.dumps("Approval reminders queued"),
    }
