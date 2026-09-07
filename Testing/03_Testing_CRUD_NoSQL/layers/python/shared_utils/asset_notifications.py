"""Shared asset approval routing and queued notification helpers."""

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from shared_utils.decimal import decimal_serializer
from shared_utils.dynamodb import normalize_string, query_all, query_first

TIER_POSITION_MAP = {1: "operations manager", 2: "regional manager", 3: "branch manager"}


def get_asset_tier(assets_table, asset_id):
    """Use replacement value; unknown or invalid values require Operations."""
    if not asset_id:
        return 1
    asset = query_first(assets_table, IndexName="AssetIDIndex",
                        KeyConditionExpression=Key("assetID").eq(asset_id))
    try:
        value = Decimal(str((asset or {}).get("replacementValue")))
        if not value.is_finite() or value < 0:
            return 1
    except (InvalidOperation, ValueError, TypeError):
        return 1
    return 1 if value >= 50000 else 2 if value >= 15000 else 3


def get_recipients(users_table, tier, location=None):
    """Select managers by position, scope branches by location, then escalate."""
    for current_tier in range(tier, 0, -1):
        position = TIER_POSITION_MAP[current_tier]
        items = query_all(users_table, IndexName="PositionIndex",
                          KeyConditionExpression=Key("position").eq(position))
        recipients = {}
        for item in items:
            if current_tier == 3 and (not location or
                    normalize_string(item.get("location")) != normalize_string(location)):
                continue
            if not item.get("id") or not item.get("email"):
                continue
            recipients[item["id"]] = {
                "sub": item["id"], "email": item["email"],
                "name": " ".join(filter(None, [item.get("name"), item.get("family_name")])) or position,
            }
        if recipients:
            return list(recipients.values())
    return []


def get_ssm_parameter_value(ssm, name):
    """Resolve an SSM parameter name."""
    return ssm.get_parameter(Name=name)["Parameter"]["Value"]


def publish_notification(sqs, queue_url, notification):
    """Send a notification, including any DynamoDB numeric values."""
    sqs.send_message(QueueUrl=queue_url,
                     MessageBody=json.dumps(notification, default=decimal_serializer))


def schedule_approval_reminder(scheduler, *, name, group, role_arn, target_arn,
                               payload, delay_hours=72):
    """Create one reminder; a retry must not reset an existing schedule."""
    schedule_time = (datetime.now(timezone.utc) + timedelta(hours=delay_hours)).strftime("%Y-%m-%dT%H:%M:%S")
    try:
        scheduler.create_schedule(
            Name=name, GroupName=group, ScheduleExpression=f"at({schedule_time})",
            ScheduleExpressionTimezone="UTC", FlexibleTimeWindow={"Mode": "OFF"},
            Target={"Arn": target_arn, "RoleArn": role_arn,
                    "Input": json.dumps(payload, default=decimal_serializer)},
            ActionAfterCompletion="DELETE",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "ConflictException":
            raise
