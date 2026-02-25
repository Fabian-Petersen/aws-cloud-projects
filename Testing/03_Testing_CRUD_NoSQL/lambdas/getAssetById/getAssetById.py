import json
import boto3
import os
from datetime import datetime
from botocore.config import Config

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("crud-nosql-app-assets-table")
s3 = boto3.client(
    "s3",
    region_name="af-south-1",
    config=Config(
        s3={"addressing_style": "virtual"},
        signature_version="s3v4",
        region_name="af-south-1"
    )
)

PRESIGN_EXPIRES_SECONDS = int(os.getenv("PRESIGN_EXPIRES_SECONDS", "900"))  # 15 min default

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



def lambda_handler(event, context):
    try:
        # Path param from API Gateway
        request_id = event.get("pathParameters", {}).get("id")

        if not request_id:
            return _response(400, {"message": "Missing request id"})

        # Use GetItem (fast, exact match)
        result = table.get_item(
            Key={"id": request_id}
        )

        item = result.get("Item")

        if not item:
            return _response(404, {"message": "Asset not found"})

        if "createdAt" in item:
            item["createdAt"] = to_human_date(item["createdAt"])

        # ✅ Add presigned URLs to each image
        item = add_presigned_urls(item)
        return _response(200, item)

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