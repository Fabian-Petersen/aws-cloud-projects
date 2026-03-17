import json
import os
import boto3
from datetime import datetime
from boto3.dynamodb.conditions import Key
from botocore.config import Config

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("crud-nosql-app-maintenance-request-table")
s3 = boto3.client(
    "s3",
    region_name="af-south-1",
    config=Config(
        s3={"addressing_style": "virtual"},
        signature_version="s3v4",
        region_name="af-south-1"
    )
)

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Credentials": "true"
}

PRESIGN_EXPIRES_SECONDS = int(os.getenv("PRESIGN_EXPIRES_SECONDS", "900")) 

def to_human_date(iso_string: str) -> str:
    dt = datetime.fromisoformat(iso_string)
    return dt.strftime("%d %b %Y, %H:%M")

def add_presigned_urls(item: dict) -> dict:
    """
    Expected item shape includes:
      "images": [{"bucket": "...", "key": "maintenance/.../file.webp"}, ...]
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
        filename = img.get("filename", key.split("/")[-1])
        new_img = {
            "key": key,
            "filename": filename,
            "url": None
        }
        if bucket and key:
            try:
                new_img["url"] = s3.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={"Bucket": bucket, "Key": key},
                    ExpiresIn=PRESIGN_EXPIRES_SECONDS,
                )
            except Exception as e:
                print("Presign error:", e)
        new_images.append(new_img)
    item["images"] = new_images
    return item

def lambda_handler(event, context):
    # print("Event:", event)
    try:
        request_id = event.get("pathParameters", {}).get("id")
        print(f"Request ID: {request_id}")

        if not request_id:
            return _response(400, {"message": "Missing request id"})

        result = table.query(
            KeyConditionExpression=Key("id").eq(request_id)
        )

        # print("result:", result)

        items = result.get("Items", [])

        if not items:
            return _response(404, {"message": "Maintenance request not found"})

        item = items[0]

        if "jobCreated" in item:
            item["jobCreated"] = to_human_date(item["jobCreated"])
            
        item = add_presigned_urls(item)
        return _response(200, item)

    except Exception as exc:
        print("Error:", str(exc))
        return _response(500, {"message": "Internal server error"})

def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": HEADERS,
        "body": json.dumps(body),
    }