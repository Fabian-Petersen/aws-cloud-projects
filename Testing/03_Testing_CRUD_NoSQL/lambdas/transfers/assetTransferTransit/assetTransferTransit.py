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

# ---------------------------------------------------------------------------- #
#                       Get location asset will move to                       #
# ---------------------------------------------------------------------------- #


def get_location(transferId):
    """
    Returns the location the asset will be transferred to.
    """

    response = users_table.query(
        IndexName="IdIndex",
        KeyConditionExpression=Key("id").eq(transferId)
    )

    items = response.get("Items", [])

    if not items:
        return None

    location = items[0].get("locationTo")

    return location

# ---------------------------------------------------------------------------- #
#                       Get Recipient asset will move to                       #
# ---------------------------------------------------------------------------- #


def get_branch_manager(location):
    """
    Returns the preferred recipient for a location.

    Priority:
    1. Manager
    2. Supervisor
    """

    response = users_table.query(
        IndexName="LocationIndex",
        KeyConditionExpression=Key("location").eq(location)
    )

    items = response.get("Items", [])

    if not items:
        return None

    # First preference: Branch Manager
    for user in items:
        if user.get("position", "").lower() == "manager":
            return user

    # Second preference: Branch Supervisor
    for user in items:
        if user.get("position", "").lower() == "supervisor":
            return user

    # No suitable recipient found
    return None


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
            old_image.get("status") != "approved"
            or new_image.get("status") != "in-transit"
        ):
            continue

        transfer_id = new_image["id"]
        location = new_image["locationTo"]
        recipient = get_branch_manager(location)
        approved_date = new_image["approvedDate"]
        asset_id = new_image["assetID"]
        expectedDate = new_image["expectedDate"]

        ttl = int(
            (datetime.now(timezone.utc) + timedelta(days=90)).timestamp()
        )

        # ---------------------------------------------------------------------------- #
        #                           Notification for Recipient                         #
        # ---------------------------------------------------------------------------- #

        if recipient:

            recipient_notification = {
                "id": str(uuid.uuid4()),
                "recipientSub": recipient["id"],
                "transferId": transfer_id,
                "notificationCreated": approved_date,
                "status": "UNREAD",
                "priority": "NORMAL",
                "type": "TRANSFER_TRANSIT",
                "title": "Asset In Transit",
                "assetId": asset_id,
                "message": (
                    f"Asset {asset_id} is in transit, expected date {expectedDate}"
                ),
                "channels": [
                    "IN_APP",
                    "EMAIL"
                ],
                "ttl": ttl
            }

            publish_notification(recipient_notification)

    return {
        "statusCode": 200,
        "body": json.dumps("Notifications queued.")
    }
