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

TABLE_NAME = "crud-nosql-app-comments-table"

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
        claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})

        # Validate required fields
        required_fields = ["message", "request_id"]
        for field in required_fields:
            if field not in data:
                return _response(400, {"message": f"Missing field: {field}"})

        # Create backend meta data
        item_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        # data from the cognito user sign-in
        user_id = claims.get("sub")
        comment_by = f'{claims.get("name", "")} {claims.get("family_name", "")}'

        # Save metadata to DynamoDB
        item = {
            "id": item_id, #$ created on backend
            "createdAt": created_at, #$ created on backend
            "comment_sub": user_id, #$ created on backend (cognito id)
            "comment_by": comment_by, #$ created on backend (name and surname)
            "comment": data["comment"],
            "request_id" :data["request_id"]
        }

        table.put_item(Item=item)

    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": "Internal server error"})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": HEADERS,
        "body": json.dumps(body),
    }
