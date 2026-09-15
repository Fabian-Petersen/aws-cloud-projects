"""Create asset records and issue presigned URLs for their image uploads.

The DynamoDB table uses ``id`` as its primary key and exposes optional
``assetID`` and ``serialNumber`` attributes through sparse secondary indexes.
Consequently, optional empty values must be omitted from stored items rather
than written as empty strings.
"""

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
    """Validate and create an asset from an API Gateway proxy request.

    A barcode (``assetID``) is optional for low-value and rental assets but is
    required for every other asset type. When no barcode is supplied, the
    handler skips the ``AssetIDIndex`` duplicate lookup and omits the attribute
    from the saved item so DynamoDB treats the index as sparse. Non-empty asset
    IDs and serial numbers are checked for duplicates before the record is
    created. Image metadata is converted into presigned S3 upload URLs; the
    image list on the new record remains empty until uploads are processed.

    Args:
        event: API Gateway proxy event whose ``body`` contains the JSON asset.
        context: Lambda runtime context. It is accepted but not used.

    Returns:
        An API Gateway proxy response containing upload URLs on success or an
        error message when validation, duplicate checking, or persistence fails.
    """
    print("event:", json.dumps(event))

    try:
        if not event.get("body"):
            return _response(400, {"message": "Missing request body"})

        data = json.loads(event["body"])

        # Validate required fields
        required_fields = [
            "location",
            "business_unit",
            "area",
            "equipment",
            "assetType",
            "category",
            "replacementValue",
            "condition",
        ]

        for field in required_fields:
            if field not in data:
                return _response(400, {"message": f"Missing field: {field}"})

        asset_id = str(data.get("assetID") or "").strip()
        asset_type = data["assetType"]
        asset_id_optional_types = {"low value asset", "rental"}

        if asset_type not in asset_id_optional_types and not asset_id:
            return _response(
                400,
                {"message": "Asset ID is required for this asset type"},
            )

        # An empty string cannot be used as the AssetIDIndex partition key.
        # Low-value and rental assets without a barcode are omitted from this
        # sparse index instead.
        if asset_id:
            existing_assetID = table.query(
                IndexName="AssetIDIndex",
                KeyConditionExpression=Key("assetID").eq(asset_id),
            ).get("Items", [])
        else:
            existing_assetID = []

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
                    "type": "images"
                }
            )

            print("presigned_urls", presigned_urls)

        # Save metadata to DynamoDB
        item = {
            "id": item_id,
            "createdAt": created_at,
            "location": data["location"],
            "business_unit": data["business_unit"],
            "area": data["area"],
            "equipment": data["equipment"],
            "assetType": data["assetType"],
            "category": data["category"],
            "condition": data["condition"],
            "replacementValue": data["replacementValue"],
            "additional_notes": data.get("additional_notes", ""),
            "images": [],
        }

        if asset_id:
            item["assetID"] = asset_id

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
    """Build a JSON API Gateway proxy response with the endpoint CORS headers.

    Args:
        status_code: HTTP status code returned to the client.
        body: JSON-serializable response payload.

    Returns:
        A mapping containing ``statusCode``, the shared response headers, and a
        JSON-encoded ``body``.
    """
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
