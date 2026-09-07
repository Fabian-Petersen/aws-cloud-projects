"""Notify the responsible managers when a pending disposal request is created."""

import json
import os
import uuid
from datetime import datetime, timedelta, timezone

import boto3
from boto3.dynamodb.types import TypeDeserializer
from shared_utils.asset_notifications import (
    get_asset_tier, get_recipients, get_ssm_parameter_value,
    publish_notification, schedule_approval_reminder,
)
from shared_utils.to_human_date import get_local_now

sqs = boto3.client("sqs")
ssm = boto3.client("ssm")
scheduler = boto3.client("scheduler")
dynamodb = boto3.resource("dynamodb")
users_table = dynamodb.Table("crud-nosql-app-users-table")
assets_table = dynamodb.Table("crud-nosql-app-assets-table")
deserializer = TypeDeserializer()

NOTIFICATION_QUEUE_URL = os.getenv("NOTIFICATION_QUEUE_URL", "/crud-nosql/sqs")
SCHEDULER_ROLE_ARN = os.getenv("SCHEDULER_ROLE_ARN", "/crud-nosql/scheduler_approval/scheduler_role_arn")
REMINDER_TARGET_ARN = os.getenv("REMINDER_TARGET_ARN", "/crud-nosql/disposal_approval/reminder_target_arn")
SCHEDULER_GROUP_NAME = os.getenv("SCHEDULER_GROUP_NAME", "/crud-nosql/scheduler_approval/scheduler_group_name")


def build_notification(recipient, disposal):
    """Build one request-level notification, including unidentified assets."""
    assets = disposal["assets"]
    asset_id = assets[0].get("assetID") if len(assets) == 1 else None
    description = f"asset {asset_id}" if asset_id else f"{len(assets)} asset(s)"
    return {
        "notificationCreated": get_local_now(),
        "id": str(uuid.uuid4()),
        "recipientSub": recipient["sub"],
        "recipientEmail": recipient["email"],
        "type": "OPEN_DISPOSAL",
        "title": "Asset Disposal Request",
        "message": f"Please review the disposal request for {description}.",
        "location": disposal.get("location", ""),
        "assetId": asset_id,
        "disposalId": disposal["disposalId"],
        "status": "UNREAD",
        "priority": "NORMAL",
        "channels": ["IN_APP", "EMAIL"],
        "ttl": int((datetime.now(timezone.utc) + timedelta(days=90)).timestamp()),
    }


def lambda_handler(event, context):
    """Consume SQS-wrapped EventBridge INSERT events from the disposal table.

    Route the whole request to the highest tier required by any asset, using
    the same per-asset value thresholds as transfers. Unknown assets require
    Operations. Publish once per recipient and schedule once per request.
    Errors propagate so SQS can retry rather than silently discard requests.
    """
    for record in event["Records"]:
        detail = json.loads(record["body"])["detail"]
        if detail["eventName"] != "INSERT":
            continue
        disposal = {key: deserializer.deserialize(value)
                    for key, value in detail["dynamodb"]["NewImage"].items()}
        if disposal.get("status") != "pending":
            continue
        disposal_id = disposal.get("disposalId")
        assets = disposal.get("assets")
        if not disposal_id or not isinstance(assets, list) or not assets:
            raise ValueError("Disposal request must contain disposalId and a non-empty assets list")
        tier = min(get_asset_tier(assets_table, asset.get("assetID")) for asset in assets)
        recipients = get_recipients(users_table, tier, disposal.get("location"))
        if not recipients:
            raise ValueError(f"No disposal approval recipients found for {disposal_id}")

        # Resolve configuration before publishing any notifications.
        queue_url = get_ssm_parameter_value(ssm, NOTIFICATION_QUEUE_URL)
        role_arn = get_ssm_parameter_value(ssm, SCHEDULER_ROLE_ARN)
        target_arn = get_ssm_parameter_value(ssm, REMINDER_TARGET_ARN)
        group = get_ssm_parameter_value(ssm, SCHEDULER_GROUP_NAME)
        for recipient in recipients:
            publish_notification(sqs, queue_url, build_notification(recipient, disposal))
        schedule_approval_reminder(
            scheduler, name=disposal.get("schedule_name") or f"disposal-{disposal_id}-timeout",
            group=group, role_arn=role_arn, target_arn=target_arn,
            payload={"type": "APPROVAL_REMINDER", "disposalId": disposal_id,
                     "disposal": disposal, "recipients": recipients}, delay_hours=72,
        )
    return {"statusCode": 200, "body": json.dumps("Notifications queued")}
