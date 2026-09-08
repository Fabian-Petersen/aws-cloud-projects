"""
This function receives the DynamoDB image of an asset disposal once the
disposal is completed.

The function:
1. Confirms the disposal status transitioned from approved -> disposed.
2. Updates every asset in the disposal request:
   - condition = "disposed"
   - disposalId
   - disposalCreated
3. Notifies the branch manager/supervisor that each asset was disposed.
"""

import json
import os
import uuid
import boto3

from boto3.dynamodb.types import TypeDeserializer
from boto3.dynamodb.conditions import Key
from datetime import datetime, timezone, timedelta


# ---------------------------------------------------------------------------- #
#                                   CLIENTS                                    #
# ---------------------------------------------------------------------------- #

sqs = boto3.client("sqs")
ssm = boto3.client("ssm")

dynamodb = boto3.resource("dynamodb")
deserializer = TypeDeserializer()


# ---------------------------------------------------------------------------- #
#                                ENVIRONMENT                                   #
# ---------------------------------------------------------------------------- #

NOTIFICATION_QUEUE_URL = os.getenv(
    "NOTIFICATION_QUEUE_URL",
    "/crud-nosql/sqs"
)


# ---------------------------------------------------------------------------- #
#                               DYNAMODB TABLES                                #
# ---------------------------------------------------------------------------- #

users_table = dynamodb.Table("crud-nosql-app-users-table")

assets_table = dynamodb.Table("crud-nosql-app-assets-table")


# ---------------------------------------------------------------------------- #
#                               GET SQS URL                                    #
# ---------------------------------------------------------------------------- #

def get_sqs_url():
    """
    Fetch the notifications SQS queue URL from SSM Parameter Store.
    """

    response = ssm.get_parameter(Name=NOTIFICATION_QUEUE_URL)

    return response["Parameter"]["Value"]


# ---------------------------------------------------------------------------- #
#                             DESERIALIZE IMAGE                                #
# ---------------------------------------------------------------------------- #

def deserialize(image):
    """
    Convert a DynamoDB Stream image into a normal Python dictionary.
    """

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
    """

    sqs_url = get_sqs_url()

    print(
        f"Publishing notification to SQS for "
        f"recipient={notification.get('recipientSub')}"
    )

    sqs.send_message(
        QueueUrl=sqs_url,
        MessageBody=json.dumps(notification)
    )


# ---------------------------------------------------------------------------- #
#                           GET BRANCH MANAGER                                 #
# ---------------------------------------------------------------------------- #

def get_branch_manager(location):
    """
    Return the preferred notification recipient for the branch.

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

    # First preference: Manager
    for user in items:
        if user.get("position", "").lower() == "manager":
            return user

    # Second preference: Supervisor
    for user in items:
        if user.get("position", "").lower() == "supervisor":
            return user

    return None


# ---------------------------------------------------------------------------- #
#                           UPDATE ASSET CONDITION                             #
# ---------------------------------------------------------------------------- #

def update_asset_condition(
    asset_id: str,
    disposal_id: str,
    disposal_created: str
):
    """
    Mark an asset as disposed.

    The asset is located using the AssetIDIndex GSI.

    Fields updated:
    - condition = "disposed"
    - disposalId
    - disposalCreated
    """

    print(
        f"Looking up asset {asset_id} using AssetIDIndex"
    )

    response = assets_table.query(
        IndexName="AssetIDIndex",
        KeyConditionExpression=Key("assetID").eq(asset_id)
    )

    items = response.get("Items", [])

    if not items:
        raise ValueError(
            f"Asset not found in assets table: {asset_id}"
        )

    asset = items[0]

    print(
        f"Found asset: "
        f"id={asset['id']}, "
        f"assetID={asset_id}, "
        f"currentCondition={asset.get('condition')}"
    )

    response = assets_table.update_item(
        Key={
            "id": asset["id"]
        },
        UpdateExpression=(
            "SET #condition = :condition, "
            "disposalId = :disposalId, "
            "disposalCreated = :disposalCreated"
        ),
        ExpressionAttributeNames={
            "#condition": "condition"
        },
        ExpressionAttributeValues={
            ":condition": "disposed",
            ":disposalId": disposal_id,
            ":disposalCreated": disposal_created
        },
        ReturnValues="ALL_NEW"
    )

    updated_asset = response.get(
        "Attributes",
        {}
    )

    print(
        f"Asset {asset_id} successfully updated: "
        f"condition={updated_asset.get('condition')}, "
        f"disposalId={updated_asset.get('disposalId')}"
    )

    return updated_asset


# ---------------------------------------------------------------------------- #
#                                LAMBDA HANDLER                                #
# ---------------------------------------------------------------------------- #

def lambda_handler(event, context):

    print(
        "event:",
        json.dumps(event)
    )

    for record in event.get("Records", []):

        try:
            # ---------------------------------------------------------------- #
            #                         PARSE SQS MESSAGE                        #
            # ---------------------------------------------------------------- #

            body = json.loads(
                record["body"]
            )

            detail = body["detail"]

            dynamodb_record = detail["dynamodb"]

            new_image = deserialize(
                dynamodb_record["NewImage"]
            )

            old_image = deserialize(
                dynamodb_record.get(
                    "OldImage",
                    {}
                )
            )

            old_status = old_image.get("status")

            new_status = new_image.get("status")

            print(f"Old status: {old_status}")

            print(f"New status: {new_status}")

            print("New image:", json.dumps(new_image, default=str))

            # ---------------------------------------------------------------- #
            #                 ONLY PROCESS APPROVED -> DISPOSED                #
            # ---------------------------------------------------------------- #

            if (old_status != "approved" or new_status != "disposed"):
                print(
                    f"Skipping record. "
                    f"Status transition "
                    f"{old_status} -> {new_status} "
                    f"is not supported."
                )

                continue

            # ---------------------------------------------------------------- #
            #                        DISPOSAL DETAILS                           #
            # ---------------------------------------------------------------- #

            disposal_id = new_image["disposalId"]

            disposal_created = new_image["disposalCreated"]

            location = new_image["location"]

            assets = new_image.get("assets", [])

            disposed_details = (new_image.get("disposed") or {})

            disposed_date = (disposed_details.get("disposedDate"))

            disposal_method = (disposed_details.get("disposalMethod"))

            print(
                f"Processing disposal: "
                f"disposalId={disposal_id}, "
                f"location={location}, "
                f"assetCount={len(assets)}"
            )

            # ---------------------------------------------------------------- #
            #                    VALIDATE ASSETS EXIST                          #
            # ---------------------------------------------------------------- #

            if not assets:

                print(
                    f"No assets found for disposal "
                    f"{disposal_id}"
                )

                continue

            # ---------------------------------------------------------------- #
            #                     GET NOTIFICATION RECIPIENT                   #
            # ---------------------------------------------------------------- #

            recipient = get_branch_manager(location)

            if not recipient:

                print(
                    f"No manager or supervisor "
                    f"found for location {location}. "
                    f"Assets will still be updated."
                )

            # ---------------------------------------------------------------- #
            #                          TTL                                     #
            # ---------------------------------------------------------------- #

            ttl = int((datetime.now(timezone.utc)
                       + timedelta(days=90)).timestamp())

            # ---------------------------------------------------------------- #
            #                       PROCESS ALL ASSETS                          #
            # ---------------------------------------------------------------- #

            for asset in assets:

                asset_id = asset.get("assetID")

                if not asset_id:

                    print(
                        "Skipping asset because "
                        "assetID is missing."
                    )

                    continue

                print(
                    f"Processing disposed asset: "
                    f"{asset_id}"
                )

                # ------------------------------------------------------------ #
                #                   UPDATE ASSET RECORD                         #
                # ------------------------------------------------------------ #

                update_asset_condition(
                    asset_id=asset_id,
                    disposal_id=disposal_id,
                    disposal_created=disposal_created
                )

                print(
                    f"Asset {asset_id} marked "
                    f"as disposed."
                )

                # ------------------------------------------------------------ #
                #                   NO RECIPIENT FOUND                          #
                # ------------------------------------------------------------ #

                if not recipient:
                    continue

                # ------------------------------------------------------------ #
                #                       NOTIFICATION                            #
                # ------------------------------------------------------------ #

                recipient_notification = {
                    "id": str(
                        uuid.uuid4()
                    ),
                    "recipientSub": recipient[
                        "id"
                    ],
                    "disposalId": disposal_id,
                    "notificationCreated": (
                        disposed_date
                        or new_image.get(
                            "dateUpdated"
                        )
                        or disposal_created
                    ),
                    "status": "UNREAD",
                    "priority": "NORMAL",
                    "type": "ASSET_DISPOSED",
                    "title": "Asset Disposed",
                    "assetId": asset_id,
                    "location": location,
                    "message": (
                        f"Asset {asset_id} was disposed "
                        f"at location {location}"
                        + (
                            f" using disposal method "
                            f"{disposal_method}."
                            if disposal_method
                            else "."
                        )
                    ),
                    "channels": [
                        "IN_APP",
                        "EMAIL"
                    ],
                    "ttl": ttl
                }

                publish_notification(recipient_notification)

                print(
                    f"Notification queued for "
                    f"asset={asset_id}, "
                    f"recipient={recipient['id']}"
                )

        except Exception as e:

            print(
                f"Error processing record: "
                f"{str(e)}"
            )

            raise

    return {
        "statusCode": 200,
        "body": json.dumps(
            "Processed."
        )
    }
