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

TABLE_NAME = "crud-nosql-app-contractor-table"
BUCKET_NAME = "crud-nosql-app-images"

table = dynamodb.Table(TABLE_NAME)

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "POST,PUT,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With",
    "Access-Control-Allow-Credentials": "true"
}

def lambda_handler(event, context):
    try:
        if not event.get("body"):
            return _response(400, {"message": "Missing request body"})

        data = json.loads(event["body"])

        # $ Check if the contractor already exist "Check how i can identify unique contractors"
        # existing_assetID = table.scan(
        #     FilterExpression="assetID = :assetID",
        #     ExpressionAttributeValues={
        #         ":assetID": data.get("assetID"),
        #     }
        # ).get("Items", [])
        
        # if existing_assetID:
        #     return _response(400, {"message": f"Asset with Asset ID {existing_assetID[0].get('assetID')} already exists"})

        # Validate required fields
        required_fields = ["business_unit","area","equipment", "location", "assetID", "serialNumber", "condition", "additional_notes"]
        for field in required_fields:
            if field not in data:
                return _response(400, {"message": f"Missing field: {field}"})

        # Create backend meta data
        item_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

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
            "serialNumber": data["serialNumber"],
            "additional_notes": data["additional_notes"],
            "images": []  # Will be updated by S3-triggered Lambda later
        }

        table.put_item(
            Item=item, 
            ConditionExpression="attribute_not_exists(assetID) AND attribute_not_exists(serialNumber)" # Ensure that no item with the same assetID already exists
            )
        
        return _response(200, {"message": "Contractor successfully created"})

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