"""
This function received the Image of an asset once transfer is completed. The function then notifiy the requestor that the asset was received.
"""


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

# ---------------------------------------------------------------------------- #
#                                DynamoDB Tables                               #
# ---------------------------------------------------------------------------- #
users_table = dynamodb.Table("crud-nosql-app-users-table")
assets_table = dynamodb.Table("crud-nosql-app-assets-table")


# ---------------------------------------------------------------------------- #
#                               GET SQS URL FROM SSM                           #
# ---------------------------------------------------------------------------- #
def get_sqs_url():
    """Fetch the queue URL from the SSM Parameter Store"""
    response = ssm.get_parameter(Name=NOTIFICATION_QUEUE_URL)
    return response["Parameter"]["Value"]


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


# ---------------------------------------------------------------------------- #
#                             UPDATE ASSET LOCATION                            #
# ---------------------------------------------------------------------------- #

def update_asset_location(asset_id, location):
    """
    Updates the asset's location using the assetID GSI.
    """

    print(f"Looking up asset {asset_id} using AssetIDIndex")

    response = assets_table.query(
        IndexName="AssetIDIndex",
        KeyConditionExpression=Key("assetID").eq(asset_id)
    )

    items = response.get("Items", [])

    if not items:
        raise ValueError(f"Asset not found: {asset_id}")

    asset = items[0]

    print(
        f"Found asset: id={asset['id']}, "
        f"currentLocation={asset.get('location')}"
    )

    assets_table.update_item(
        Key={
            "id": asset["id"]
        },
        UpdateExpression="SET #location = :location",
        ExpressionAttributeNames={
            "#location": "location"
        },
        ExpressionAttributeValues={
            ":location": location
        }
    )


def lambda_handler(event, context):
    print("event:", json.dumps(event))

    for record in event.get("Records", []):
        try:
            body = json.loads(record["body"])
            detail = body["detail"]
            dynamodb_record = detail["dynamodb"]

            new_image = deserialize(dynamodb_record["NewImage"])
            old_image = deserialize(dynamodb_record.get("OldImage", {}))

            old_status = old_image.get("status")
            new_status = new_image.get("status")

            print(f"Old status: {old_status}")
            print(f"New status: {new_status}")
            print(f"New image: {json.dumps(new_image, default=str)}")

            # Only process an in-transit -> completed transition
            if old_status != "in-transit" or new_status != "completed":
                print(
                    f"Skipping record. Status transition "
                    f"{old_status} -> {new_status} is not supported."
                )
                continue

            transfer_id = new_image["id"]
            asset_id = new_image["assetID"]
            location = new_image["locationTo"]

            print(
                f"Processing received transfer: "
                f"transferId={transfer_id}, "
                f"assetId={asset_id}, "
                f"location={location}"
            )

            # ------------------------------------------------------------
            # Update asset location
            # ------------------------------------------------------------

            update_asset_location(asset_id, location)

            print(
                f"Asset {asset_id} location updated to {location}"
            )

            # ------------------------------------------------------------
            # Find notification recipient
            # ------------------------------------------------------------

            recipient = get_branch_manager(location)

            if not recipient:
                print(
                    f"No branch manager/supervisor found for location "
                    f"{location}. Asset was updated, but no notification "
                    f"will be sent."
                )
                continue

            print(
                f"Notification recipient found: {recipient}"
            )

            # ------------------------------------------------------------
            # Notification
            # ------------------------------------------------------------

            ttl = int(
                (
                    datetime.now(timezone.utc)
                    + timedelta(days=90)
                ).timestamp()
            )

            recipient_notification = {
                "id": str(uuid.uuid4()),
                "recipientSub": recipient["id"],
                "transferId": transfer_id,
                "notificationCreated": new_image.get(
                    "receivedDate",
                    new_image.get("approvedDate")
                ),
                "status": "UNREAD",
                "priority": "NORMAL",
                "type": "TRANSFER_RECEIVED",
                "title": "Asset Received",
                "assetId": asset_id,
                "message": (
                    f"Asset {asset_id} received at location {location}"
                ),
                "channels": [
                    "IN_APP",
                    "EMAIL"
                ],
                "ttl": ttl
            }

            publish_notification(recipient_notification)

            print(
                f"Notification queued for recipient "
                f"{recipient['id']}"
            )

        except Exception as e:
            print(
                f"Error processing record: {str(e)}"
            )
            raise

    return {
        "statusCode": 200,
        "body": json.dumps("Processed.")
    }
