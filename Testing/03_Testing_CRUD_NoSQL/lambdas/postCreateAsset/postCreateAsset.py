import json
import boto3
import uuid
from datetime import datetime, timezone
from botocore.config import Config

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client(
    "s3",
    region_name="af-south-1",
    config=Config(
        s3={"addressing_style": "virtual"},
        signature_version="s3v4",
        region_name="af-south-1"
    )
)

TABLE_NAME = "crud-nosql-app-assets-table"
BUCKET_NAME = "crud-nosql-app-images"

table = dynamodb.Table(TABLE_NAME)

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST,PUT,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With"
}

def lambda_handler(event, context):
    try:
        if not event.get("body"):
            return _response(400, {"message": "Missing request body"})

        data = json.loads(event["body"])

        # Check if the asset already exist with the same assetID and serialNumber
        existing_item = table.scan(
            FilterExpression="assetID = :assetID AND serialNumber = :serialNumber",
            ExpressionAttributeValues={
                ":assetID": data.get("assetID"),
                ":serialNumber": data.get("serialNumber")
            }
        ).get("Items", [])
        
        if existing_item:
            return _response(400, {"message": "Asset with this assetID or Serial Number already exists"})

        # Validate required fields
        required_fields = ["business_unit","category","equipment", "location", "assetID", "serialNumber", "condition", "additional_notes"]
        for field in required_fields:
            if field not in data:
                return _response(400, {"message": f"Missing field: {field}"})

        # Create backend meta data
        item_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        presigned_urls = []

        # Check if frontend included any files
        for file_info in data.get("images", []):
            filename = file_info.get("filename")
            content_type = file_info.get("content_type", "application/octet-stream")
            if not filename:
                continue

        
        # Generate presigned urls
            key = f"assets/{item_id}/{filename}"
            url = s3.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": BUCKET_NAME,
                    "Key": key,
                    "ContentType": content_type
                },
                ExpiresIn=3600  # 1 hour
            )

            # The config above force the url to be af-south-1 region and the code below check if the url is region specific.
            if "s3.af-south-1.amazonaws.com" not in url:
                raise Exception("Presigned URL generated with incorrect S3 endpoint")

            presigned_urls.append({"filename": filename, "url": url, "key": key, "content_type": content_type})

        # Save metadata to DynamoDB
        item = {
            "id": item_id,
            "createdAt": created_at,
            "business_unit": data["business_unit"],
            "category": data["category"],
            "equipment": data["equipment"],
            "condition": data["condition"],
            "location": data["location"],
            "assetID": data["assetID"],
            "serialNumber": data["serialNumber"],
            "additional_notes": data["additional_notes"],
            "images": []  # Will be updated by S3-triggered Lambda later
        }

        table.put_item(
            Item=item, 
            ConditionExpression="attribute_not_exists(assetID)" # Ensure that no item with the same assetID already exists
            )

        return _response(200, {"form": item, "presigned_urls": presigned_urls})

    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": "Internal server error"})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": HEADERS,
        "body": json.dumps(body),
    }
