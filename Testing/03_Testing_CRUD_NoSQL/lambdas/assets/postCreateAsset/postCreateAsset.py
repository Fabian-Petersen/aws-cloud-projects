import json
import boto3
import uuid
from datetime import datetime, timezone
from botocore.config import Config
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")

s3 = boto3.client(
    "s3",
    region_name="af-south-1",
    config=Config(
        s3={"addressing_style": "virtual"},
        signature_version="s3v4",
        region_name="af-south-1",
    ),
)

TABLE_NAME = "crud-nosql-app-assets-table"
BUCKET_NAME = "crud-nosql-app-images"

table = dynamodb.Table(TABLE_NAME)

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "POST,PUT,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With",
    "Access-Control-Allow-Credentials": "true",
}


def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))

    try:
        if not event.get("body"):
            return _response(400, {"message": "Missing request body"})

        data = json.loads(event["body"])

        # Check if assetID already exists
        existing_assetID = table.query(
            IndexName="AssetIDIndex",
            KeyConditionExpression=Key("assetID").eq(data.get("assetID"))).get("Items", [])

        if existing_assetID:
            return _response(
                400,
                {
                    "message": f"Asset with Asset ID {existing_assetID[0].get('assetID')} already exists"
                },
            )

        # Check if serial number already exists
        serial_number = data.get("serialNumber")

        if not serial_number or serial_number == 0:
            existing_serialNumber = []
        else:
            existing_serialNumber = table.query(
                IndexName="SerialNumberIndex",
                KeyConditionExpression="serialNumber = :serialNumber",
                ExpressionAttributeValues={
                    ":serialNumber": serial_number,
                },
            ).get("Items", [])

        if existing_serialNumber:
            return _response(
                400,
                {
                    "message": f"Asset with Serial Number {existing_serialNumber[0].get('serialNumber')} already exists"
                },
            )

        # Validate required fields
        required_fields = [
            "business_unit",
            "area",
            "equipment",
            "location",
            "assetID",
            "serialNumber",
            "condition",
            "additional_notes",
        ]

        for field in required_fields:
            if field not in data:
                return _response(400, {"message": f"Missing field: {field}"})

        # Create backend metadata
        item_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        presigned_urls = []

        # Generate presigned URLs if images exist
        for file_info in data.get("images", []):
            filename = file_info.get("filename")
            content_type = file_info.get(
                "content_type", "application/octet-stream")

            if not filename:
                continue

            key = f"assets/{item_id}/{filename}"

            url = s3.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": BUCKET_NAME,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=3600,
            )

            if "s3.af-south-1.amazonaws.com" not in url:
                raise Exception(
                    "Presigned URL generated with incorrect S3 endpoint")

            presigned_urls.append(
                {
                    "filename": filename,
                    "url": url,
                    "key": key,
                    "content_type": content_type,
                }
            )

            print("presigned_urls", presigned_urls)

        # Save metadata to DynamoDB
        item = {
            "id": item_id,
            "createdAt": created_at,
            "business_unit": data["business_unit"],
            "area": data["area"],
            "equipment": data["equipment"],
            "condition": data["condition"],
            "location": data["location"],
            "assetID": data["assetID"],
            "additional_notes": data["additional_notes"],
            "images": [],
        }

        serial_number = data.get("serialNumber")

        if serial_number not in (None, "", 0):
            item["serialNumber"] = serial_number

        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(assetID) AND attribute_not_exists(serialNumber)",
        )

        return _response(200, {"presigned_urls": presigned_urls})

    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": "Error from lambda, internal server error"})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": HEADERS,
        "body": json.dumps(body),
    }


# Run locally
if __name__ == "__main__":
    with open("event.json") as f:
        event = json.load(f)

    result = lambda_handler(event, None)
    print(json.dumps(result, indent=2))
