import boto3
import json
import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("crud-nosql-app-assets-table")

# How many days out counts as "Due" rather than comfortably "Verified"
DUE_SOON_DAYS = int(os.environ.get("DUE_SOON_DAYS", 30))


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError


def parse_iso(date_str):
    """Parse an ISO8601 string (with or without offset) into an aware datetime."""
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def scan_all_items():
    items = []
    scan_kwargs = {
        "ProjectionExpression": "verify_status, next_verification_due, last_verified_at",
    }

    while True:
        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key

    return items


def classify_status(item, now, due_soon_cutoff):
    verify_status = (item.get("verify_status") or "").lower()
    last_verified_at = item.get("last_verified_at")
    next_due = parse_iso(item.get("next_verification_due"))

    # Never verified at all
    if verify_status != "verified" or not last_verified_at:
        return "Not Verified"

    # Verified, but no due date on record -> treat as verified
    if next_due is None:
        return "Verified"

    if next_due < now:
        return "Overdue"
    if next_due <= due_soon_cutoff:
        return "Due"
    return "Verified"


def lambda_handler(event, context):
    try:
        items = scan_all_items()

        now = datetime.now(timezone.utc)
        due_soon_cutoff = now + timedelta(days=DUE_SOON_DAYS)

        status_counts = {
            "Verified": 0,
            "Due": 0,
            "Overdue": 0,
            "Not Verified": 0,
        }

        for item in items:
            status = classify_status(item, now, due_soon_cutoff)
            status_counts[status] += 1

        total = len(items)
        verified = status_counts["Verified"]
        compliance = round((verified / total) * 100) if total > 0 else 0

        verification_data = {
            "compliance": compliance,
            "total": total,
            "statuses": [
                {"name": label, "value": status_counts[label]}
                for label in ["Verified", "Due", "Overdue", "Not Verified"]
            ],
        }

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(verification_data, default=decimal_default),
        }

    except Exception as e:
        print(f"Error fetching asset verification metrics: {e}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": "Failed to fetch asset verification metrics"}),
        }
