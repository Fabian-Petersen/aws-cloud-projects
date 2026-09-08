import json
import os
import uuid
import boto3

from boto3.dynamodb.types import TypeDeserializer
from datetime import datetime, timezone, timedelta


# ---------------------------------------------------------------------------- #
#                                AWS CLIENTS                                   #
# ---------------------------------------------------------------------------- #

sqs = boto3.client("sqs")
ssm = boto3.client("ssm")

deserializer = TypeDeserializer()


# ---------------------------------------------------------------------------- #
#                              ENVIRONMENT                                     #
# ---------------------------------------------------------------------------- #

NOTIFICATION_QUEUE_URL = os.getenv(
    "NOTIFICATION_QUEUE_URL",
    "/crud-nosql/sqs"
)


# ---------------------------------------------------------------------------- #
#                               HELPERS                                        #
# ---------------------------------------------------------------------------- #

def get_sqs_url():
    """Fetch the notifications queue URL from SSM Parameter Store."""
    response = ssm.get_parameter(Name=NOTIFICATION_QUEUE_URL)
    return response["Parameter"]["Value"]


def deserialize(image):
    """Convert a DynamoDB Stream image to a normal Python dictionary."""
    return {
        key: deserializer.deserialize(value)
        for key, value in image.items()
    }


# ---------------------------------------------------------------------------- #
#                       PUBLISH NOTIFICATION -> SQS                            #
# ---------------------------------------------------------------------------- #

def publish_notification(notification: dict) -> None:
    """
    Publish a notification to the notifications SQS queue.

    The handleNotifications Lambda consumes the message and writes it to
    the notifications DynamoDB table.
    """

    sqs_url = get_sqs_url()

    print("Publishing notification:", json.dumps(notification))
    print("SQS URL:", sqs_url)

    response = sqs.send_message(
        QueueUrl=sqs_url,
        MessageBody=json.dumps(notification)
    )

    print("SQS MessageId:", response.get("MessageId"))


# ---------------------------------------------------------------------------- #
#                              LAMBDA HANDLER                                  #
# ---------------------------------------------------------------------------- #

def lambda_handler(event, context):

    print("Event:", json.dumps(event))

    for record in event.get("Records", []):

        try:
            # ---------------------------------------------------------------- #
            # SQS body contains the EventBridge event as a JSON string
            # ---------------------------------------------------------------- #

            body = json.loads(record["body"])

            detail = body.get("detail", {})
            stream_data = detail.get("dynamodb", {})

            if not stream_data:
                print("No DynamoDB stream data found.")
                continue

            # ---------------------------------------------------------------- #
            # Deserialize DynamoDB NewImage / OldImage
            # ---------------------------------------------------------------- #

            new_image_raw = stream_data.get("NewImage")

            if not new_image_raw:
                print("No NewImage found.")
                continue

            new_image = deserialize(new_image_raw)

            old_image = deserialize(
                stream_data.get("OldImage", {})
            )

            print("NewImage:", json.dumps(new_image, default=str))
            print("OldImage:", json.dumps(old_image, default=str))

            # ---------------------------------------------------------------- #
            # Only process:
            #
            # pending -> approved
            # ---------------------------------------------------------------- #

            old_status = old_image.get("status")
            new_status = new_image.get("status")

            print(
                f"Disposal status transition: "
                f"{old_status} -> {new_status}"
            )

            if (
                old_status != "pending"
                or new_status != "approved"
            ):
                print("Not a disposal approval event. Skipping.")
                continue

            # ---------------------------------------------------------------- #
            # Disposal data
            # ---------------------------------------------------------------- #

            disposal_id = new_image.get("disposalId")
            requestor_sub = new_image.get("requestorSub")
            requestor_name = new_image.get("requestorName")
            location = new_image.get("location")

            # Approval information is stored as a nested object.
            approved = new_image.get("approved") or {}

            approved_date = (
                approved.get("approvedDate")
                or new_image.get("approvedDate")
            )

            approver_name = (
                approved.get("approvedBy")
                or new_image.get("approvedBy")
            )

            approver_sub = (
                approved.get("approvedBySub")
                or new_image.get("approvedBySub")
            )

            # ---------------------------------------------------------------- #
            # Validate required fields
            # ---------------------------------------------------------------- #

            if not disposal_id:
                print("Missing disposalId. Skipping notification.")
                continue

            if not requestor_sub:
                print(
                    f"Missing requestorSub for disposal "
                    f"{disposal_id}. Skipping notification."
                )
                continue

            if not approved_date:
                print(
                    f"Missing approvedDate for disposal "
                    f"{disposal_id}. Skipping notification."
                )
                continue

            # ---------------------------------------------------------------- #
            # TTL - notification expires after 90 days
            # ---------------------------------------------------------------- #

            ttl = int(
                (
                    datetime.now(timezone.utc)
                    + timedelta(days=90)
                ).timestamp()
            )

            # ---------------------------------------------------------------- #
            # Notification for requestor
            # ---------------------------------------------------------------- #

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
                    f"Your disposal request for {location} "
                    f"has been approved."
                ),
                "channels": [
                    "IN_APP",
                    "EMAIL"
                ],
                "ttl": ttl
            }

            print(
                "Requestor notification:",
                json.dumps(requestor_notification)
            )

            publish_notification(requestor_notification)

        except Exception as exc:
            print(
                f"Failed to process record: {exc}"
            )

            # Important:
            # raise so SQS can retry / send to DLQ
            raise

    return {
        "statusCode": 200,
        "body": json.dumps("Notifications queued.")
    }
