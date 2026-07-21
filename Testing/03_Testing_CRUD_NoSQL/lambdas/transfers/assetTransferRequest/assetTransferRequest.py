import json
import os
import uuid
from datetime import datetime, timezone, timedelta
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

import boto3

sqs = boto3.client("sqs")
ssm = boto3.client("ssm")

dynamodb = boto3.resource("dynamodb")

users_table = dynamodb.Table("crud-nosql-app-users-table")
assets_table = dynamodb.Table("crud-nosql-app-assets-table")

NOTIFICATION_QUEUE_URL = os.getenv("NOTIFICATION_QUEUE_URL",
                                   "/crud-nosql/sqs")


def get_sqs_url():
    """Fetch the queue URL from the SSM Parameter Store"""
    response = ssm.get_parameter(Name=NOTIFICATION_QUEUE_URL)
    return response["Parameter"]["Value"]

# ---------------------------------------------------------------------------- #
#                       OPEN QUESTIONS / ASSUMPTIONS                           #
# ---------------------------------------------------------------------------- #
# 1. get_recipients() assumes users_table has a GSI named "PositionIndex"
#    with partition key "position", and that each user item has "sub",
#    "email", "name", and (for Branch Managers) "location" attributes.
#    Confirm this matches the actual schema before deploying.
# 2. Location matching (tier 3) uses the transfer's own "locationFrom"
#    field (the branch the asset is currently at) rather than a location
#    stored on the asset record, since the transfer event already carries
#    it. If approval should instead be scoped to the *receiving* branch,
#    swap this to "locationTo".
# 3. If no user is found for the required position (or, for tier 3, no
#    Branch Manager matches the asset's location), the code escalates one
#    tier up rather than failing silently. Confirm that's the desired
#    behaviour vs. erroring loudly.
# ---------------------------------------------------------------------------- #


# Maps an asset tier to the job title responsible for approving it.
TIER_POSITION_MAP = {
    1: "operations manager",
    2: "regional manager",
    3: "branch manager",
}


def _stream_value(image: dict, key: str) -> str | None:
    """
    Unwraps a single attribute from a raw DynamoDB Streams NewImage/OldImage.

    DynamoDB Streams represent attributes as type-tagged maps, e.g.
    {"assetID": {"S": "abc-123"}} rather than {"assetID": "abc-123"}.
    This pulls the plain value out so it can be used directly in queries
    or comparisons.

    Args:
        image: The raw stream image dict (e.g. detail["dynamodb"]["NewImage"]).
        key: The attribute name to extract (e.g. "assetID").

    Returns:
        str | None: The unwrapped string value, or None if the key/type
        is missing.

    Example:
        >>> _stream_value({"assetID": {"S": "abc-123"}}, "assetID")
        'abc-123'
    """
    attr = image.get(key)
    if not attr:
        return None
    return attr.get("S")


def get_asset_tier(assets_table, asset_id: str) -> int:
    """
    Returns the asset tier based on the asset's replacement value, which
    determines who is required to approve a transfer of that asset.

    tier 1 - Operations Manager: replacementValue >= 50,000
    tier 2 - Regional Manager:   15,000 <= replacementValue < 50,000
    tier 3 - Branch Manager:     replacementValue < 15,000

    If the asset can't be found, or has no replacementValue on record,
    this falls back to tier 1 (Operations Manager) so a transfer is never
    left without an approver.

    Note: this only determines the tier. For tier 3, the branch location
    used to scope the approver comes from the transfer event itself
    (locationFrom) rather than from the asset record — see
    get_recipients().

    Args:
        assets_table: The boto3 DynamoDB Table resource for assets.
        asset_id: The plain string asset ID (already unwrapped from any
            DynamoDB Streams attribute map).

    Returns:
        int: The asset tier (1, 2, or 3). Always falls back to 1 rather
        than returning None, so callers can rely on always getting an int.

    Raises:
        ClientError: If the underlying DynamoDB query fails.

    Example:
        >>> get_asset_tier(assets_table, "RT-0006")
        3
    """

    try:
        response = assets_table.query(
            IndexName="AssetIDIndex",
            KeyConditionExpression=Key("assetID").eq(asset_id)
        )

        items = response.get("Items", [])

        if not items:
            print(f"Asset {asset_id} not found, defaulting to tier 1")
            return 1

        asset = items[0]

        replacement_value = asset.get("replacementValue")

        if replacement_value is None:
            print(
                f"Asset {asset_id} has no replacementValue, defaulting to tier 1")
            return 1

        replacement_value = float(replacement_value)

        if replacement_value >= 50000:
            return 1
        elif replacement_value >= 15000:
            return 2
        else:
            return 3

    except ClientError as e:
        print(f"Error retrieving asset tier: {e}")
        raise

    except Exception as exc:
        print(
            f"Unexpected error retrieving asset {asset_id}: {exc}, defaulting to tier 1")
        return 1

# ---------------------------------------------------------------------------- #
#                       GET RECIPIENTS FROM TABLE                              #
# ---------------------------------------------------------------------------- #


def get_recipients(users_table, tier: int, location: str | None = None) -> list[dict]:
    """
    Determines who should approve a transfer, based on the asset's tier
    and, for tier 3 only, the asset's location.

    Looks up all users whose "position" matches the tier's responsible
    role (see TIER_POSITION_MAP). For tier 3 (Branch Manager), results
    are further filtered to only managers whose "location" matches the
    asset's location, since a branch manager may only approve transfers
    for assets at their own branch.

    If no matching user is found (e.g. no Branch Manager at that specific
    location, or no user at all for a position), this escalates one tier
    up and retries, ultimately falling back to Operations Manager.

    Args:
        users_table: The boto3 DynamoDB Table resource for users.
        tier: The asset tier (1, 2, or 3) as returned by
            get_asset_tier_and_location().
        location: The asset's location, required to scope tier 3 lookups.
            Ignored for tier 1/2.

    Returns:
        list[dict]: A list of recipient dicts, each with "sub", "email",
        and "name", suitable for passing to build_notification(). Returns
        an empty list only if no users at all (including Operations
        Manager) can be found.

    Raises:
        ClientError: If the underlying DynamoDB query fails.

    Example:
        >>> get_recipients(users_table, 3, "maitland")
        [{"sub": "branch-mgr-sub", "email": "maitland.mgr@company.com", "name": "Jane Doe"}]
    """

    position = TIER_POSITION_MAP.get(tier, "Operations Manager")

    try:
        print(f"Querying PositionIndex for position='{position}'")
        response = users_table.query(
            IndexName="PositionIndex",
            KeyConditionExpression=Key("position").eq(position)
        )
        items = response.get("Items", [])
        print("Returned items:", response.get("Items", []))

    except ClientError as e:
        print(f"Error retrieving recipients for position '{position}': {e}")
        raise

    # Branch managers can only approve transfers for their own location
    if tier == 3:
        if location is None:
            print("No location available for tier 3 asset, escalating to tier 2")
            return get_recipients(users_table, 2)

        items = [item for item in items if item.get("location") == location]

        if not items:
            print(
                f"No Branch Manager found for location '{location}', escalating to tier 2")
            return get_recipients(users_table, 2)

    elif not items:
        if tier > 1:
            print(
                f"No users found for position '{position}', escalating to tier {tier - 1}")
            return get_recipients(users_table, tier - 1)
        print("No Operations Manager found on record; no recipients available")
        return []

    return [
        {
            "sub": item["id"],
            "email": item["email"],
            "name": f"{item.get('name', '')} {item.get('family_name', '')}".strip() or position,
        }
        for item in items
    ]

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

    # Get the current time for the update
    sast = timezone(timedelta(hours=2))
    now = datetime.now(sast).isoformat()
    created_at = now

    return {
        "notificationCreated": created_at,
        "notificationId": str(uuid.uuid4()),

        "recipientSub": recipient["sub"],
        "recipientEmail": recipient["email"],

        "type": "ASSET_TRANSFER_REQUEST",
        "title": "Asset Transfer Request",
        "message": f"Please approve the transfer of asset {asset_id}.",

        "assetId": asset_id,
        "transferId": transfer_id,

        "action": {
            "type": "OPEN_TRANSFER",
            "id": transfer_id
        },

        "status": "UNREAD",
        "priority": "NORMAL",


        "channels": [
            "IN_APP",
            "EMAIL"
        ]
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
    sqs_url = get_sqs_url()
    print("sqs_url:", sqs_url)
    sqs.send_message(
        QueueUrl=sqs_url,
        MessageBody=json.dumps(notification)
    )

# ---------------------------------------------------------------------------- #
#                       LAMBDA - HANDLER                                       #
# ---------------------------------------------------------------------------- #


def lambda_handler(event, context):
    # print("event:", event)
    """
    Entry point triggered by SQS, which itself is fed by an EventBridge
    rule watching the transfer table's DynamoDB Stream (via a Pipe).

    For each new transfer request (INSERT only):
      1. Determines the asset's approval tier (and, for tier 3, its
         location) from its replacement value, defaulting to tier 1 /
         Operations Manager if unknown.
      2. Looks up the recipient(s) responsible for approving at that
         tier, scoped to the asset's location for tier 3.
      3. Builds and publishes one notification per recipient to the
         notifications queue, to be persisted by handleNotifications.

    Args:
        event: The SQS event, where each record's body is the EventBridge
            envelope wrapping a DynamoDB Streams record.
        context: The Lambda context object (unused).

    Returns:
        dict: A standard Lambda proxy response with statusCode 200 once
        all records have been processed.

    Example:
        Triggered automatically by SQS; not typically invoked directly.
        event = {
            "Records": [
                {"body": json.dumps({
                    "detail-type": "TransferRequest",
                    "source": "asset-transfer-service",
                    "detail": {
                        "eventName": "INSERT",
                        "eventSource": "aws:dynamodb",
                        "dynamodb": {"NewImage": {
                            "id": {"S": "57110692-f68f-46b5-9fa6-1b18d7fa201c"},
                            "assetID": {"S": "RT-0006"},
                            "locationFrom": {"S": "maitland"},
                            "locationTo": {"S": "bellville"},
                        }}
                    }
                })}
            ]
        }
        lambda_handler(event, None)
    """

    for record in event["Records"]:
        body = json.loads(record["body"])
        detail = body["detail"]

        # Only process INSERT requests
        if detail["eventName"] != "INSERT":
            continue

        transfer = detail["dynamodb"]["NewImage"]
        asset_id = _stream_value(transfer, "assetID")
        location_from = _stream_value(transfer, "locationFrom")

        tier = get_asset_tier(assets_table, asset_id)
        print(f"Tier {tier} approval required for asset {asset_id}" +
              (f" at '{location_from}'" if tier == 3 else ""))

        # Determine recipients based on tier (and locationFrom, for tier 3)
        recipients = get_recipients(users_table, tier, location_from)
        print("recipients:", recipients)

        # Create one notification per recipient
        for recipient in recipients:
            notification = build_notification(
                recipient=recipient,
                transfer=transfer,
            )

            publish_notification(notification)

    return {
        "statusCode": 200,
        "body": json.dumps("Notifications queued")
    }
