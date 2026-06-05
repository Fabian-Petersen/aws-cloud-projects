from decimal import Decimal
import json
import boto3
import os
from datetime import datetime
from botocore.config import Config
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
assets_table = dynamodb.Table("crud-nosql-app-assets-table")

maintenance_table = dynamodb.Table(
    "crud-nosql-app-maintenance-action-table"
)

request_table = dynamodb.Table(
    "crud-nosql-app-maintenance-request-table"
)

transfer_table = dynamodb.Table(
    "crud-nosql-app-assets-transfer-table"
)

s3 = boto3.client(
    "s3",
    region_name="af-south-1",
    config=Config(
        s3={"addressing_style": "virtual"},
        signature_version="s3v4",
        region_name="af-south-1"
    )
)

PRESIGN_EXPIRES_SECONDS = int(
    os.getenv("PRESIGN_EXPIRES_SECONDS", "900"))  # 15 min default

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With",
    "Access-Control-Allow-Credentials": "true"
}


def to_human_date(iso_string: str) -> str:
    dt = datetime.fromisoformat(iso_string)
    return dt.strftime("%d %b %Y, %H:%M")


def add_presigned_urls(item: dict) -> dict:
    """
    Expected item shape includes:
      "images": [{"bucket": "...", "key": "assets/.../file.webp"}, ...]
    Adds:
      "url": "<presigned get url>"
    """
    images = item.get("images", [])
    if not isinstance(images, list):
        return item

    new_images = []
    for img in images:
        # Keep original entries as-is if malformed
        if not isinstance(img, dict):
            new_images.append(img)
            continue

        bucket = img.get("bucket")
        key = img.get("key")

        if bucket and key:
            try:
                url = s3.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={"Bucket": bucket, "Key": key},
                    ExpiresIn=PRESIGN_EXPIRES_SECONDS,
                )
                new_img = {**img, "url": url}
            except Exception as e:
                # Don’t fail the whole request because one image failed
                print("Presign error:", e)
                new_img = {**img, "url": None}
        else:
            new_img = {**img, "url": None}

        new_images.append(new_img)

    item["images"] = new_images
    return item


def convert_decimals(obj):
    """Recursively convert DynamoDB Decimals to JSON-serializable types."""

    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]

    if isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}

    if isinstance(obj, Decimal):
        # Return int if it's a whole number, otherwise float
        return int(obj) if obj % 1 == 0 else float(obj)

    return obj

##############################################################
############# GET ASSET MAINTENANCE HISTORY ##################
##############################################################


def get_job_description(asset_id: str, job_id: str) -> str:
    try:
        response = request_table.query(
            IndexName="AssetIdIndex",
            KeyConditionExpression=Key("assetID").eq(asset_id)
        )

        items = response.get("Items", [])

        if not items:
            return ""

        # find the exact job/request record
        for item in items:
            if item.get("id") == job_id:
                return item.get("description", "")

        return ""

    except Exception as exc:
        print(f"Error retrieving job description: {exc}")
        return ""


def get_maintenance_history(asset_id: str) -> list:
    try:
        response = maintenance_table.query(
            IndexName="AssetIdIndex",
            KeyConditionExpression=Key("assetID").eq(asset_id)
        )

        items = response.get("Items", [])

        if not items:
            return []

        return [
            {
                "id": item.get("id"),
                "jobcardNumber": item.get("jobcardNumber"),
                "description": get_job_description(item.get("assetID"), item.get("request_id")),
                "completedAt": (
                    to_human_date(item["completed_at"])
                    if item.get("completed_at")
                    else None
                ),
                "actioned_by": item.get("actioned_by"),
            }
            for item in items
        ]

    except Exception as exc:
        print(f"Error loading maintenance history: {exc}")
        return []

##############################################################
################ GET ASSET TRANSFER HISTORY ##################
##############################################################


def get_transfer_history(asset_id: str) -> list:
    try:
        response = transfer_table.get_item(
            Key={"id": asset_id}
        )

        items = response.get("Items", [])

        if not items:
            return []

        return [
            {
                "id": item.get("id"),
                "fromLocation": item.get("fromLocation"),
                "toLocation": item.get("toLocation"),
                "transferredAt": (
                    to_human_date(item["transferredAt"])
                    if item.get("transferredAt")
                    else None
                ),
                "transferredBy": item.get("transferredBy"),
            }
            for item in items
        ]

    except Exception as exc:
        print(f"Error loading transfer history: {exc}")
        return []


def lambda_handler(event, context):
    try:
        # Path param from API Gateway
        request_id = event.get("pathParameters", {}).get("id")

        if not request_id:
            return _response(400, {"message": "Missing request id"})

        # Use GetItem (fast, exact match)
        result = assets_table.get_item(
            Key={"id": request_id}
        )

        item = result.get("Item")
        # convert the number to a float to prevent decimal error
        if isinstance(item.get("replacementValue"), Decimal):
            item["replacementValue"] = float(item["replacementValue"])

        if not item:
            return _response(404, {"message": "Asset not found"})

        if "createdAt" in item:
            item["createdAt"] = to_human_date(item["createdAt"])

         # $ Asset history
        asset_id = item.get("assetID")

        item["maintenanceHistory"] = (
            get_maintenance_history(asset_id)
            if asset_id
            else []
        )

        item["transferHistory"] = (
            get_transfer_history(asset_id)
            if asset_id
            else []
        )

        # ✅ Add presigned URLs to each image
        item = add_presigned_urls(item)
        print("item:", item)
        return _response(200, convert_decimals(item))

    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": "Error from lambda, internal server error"})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": HEADERS,
        "body": json.dumps(body),
    }

    # Run the lambda locally with the events.json file to test
if __name__ == "__main__":
    with open("event.json") as f:
        event = json.load(f)

    result = lambda_handler(event, None)
    print(json.dumps(result, indent=2))
