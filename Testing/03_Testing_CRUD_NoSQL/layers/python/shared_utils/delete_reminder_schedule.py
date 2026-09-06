"""Reusable EventBridge Scheduler reminder cleanup helper."""

import os

import boto3
from botocore.exceptions import ClientError


ssm = boto3.client("ssm")
scheduler = boto3.client("scheduler")


def delete_reminder_schedule(schedule_id: str) -> None:
    """Delete an EventBridge Scheduler schedule by its ID.

    Missing schedules are ignored so reminder cleanup is idempotent.

    Args:
        schedule_id: Full EventBridge Scheduler schedule ID to delete.

    Returns:
        None.

    Raises:
        botocore.exceptions.ClientError: If AWS Scheduler returns an error
            other than ``ResourceNotFoundException``.
    """
    scheduler_group_name = ssm.get_parameter(
        Name=os.getenv(
            "SCHEDULER_GROUP", "/crud-nosql/scheduler_approval/scheduler_group_name"
        )
    )["Parameter"]["Value"]

    try:
        scheduler.delete_schedule(
            GroupName=scheduler_group_name,
            Name=schedule_id,
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "ResourceNotFoundException":
            raise
