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

TABLE_NAME = "crud-nosql-app-maintenance-action-table"
TABLE_NAME_REQUESTS = "crud-nosql-app-maintenance-request-table"
BUCKET_NAME = "crud-nosql-app-images"

table = dynamodb.Table(TABLE_NAME)
table_requests = dynamodb.Table(TABLE_NAME_REQUESTS)

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
        claims = event["requestContext"]["authorizer"]["jwt"]["claims"] # Get the user information from the authoriser token.

        # Validate required fields
        required_fields = ["start_time", "end_time", "total_km", "work_order_number", "work_completed", "status", "root_cause", "findings","signature", "selectedRowId"]
        for field in required_fields:
            if field not in data:
                return _response(400, {"message": f"Missing field: {field}"})

        # Create backend meta data
        item_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        
        # data from the cognito user sign-in
        user_id = claims["sub"]
        actioned_by = f'{claims.get("name", "")} {claims.get("family_name", "")}'

        presigned_urls = []

        # Check if frontend included any files
        for file_info in data.get("images", []):
            filename = file_info.get("filename")
            content_type = file_info.get("content_type", "application/octet-stream")
            if not filename:
                continue

        # Generate presigned urls
            key = f"maintenance_action/{item_id}/{filename}"
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
            "id": item_id, #$ created on backend
            "actionCreated": created_at, #$ created on backend
            "request_id": data["selectedRowId"], #$ created on backend
            "action_sub": user_id,  #$ created on backend
            "actioned_by": actioned_by, #$ created on backend
            "start_time": data["start_time"],
            "end_time": data["end_time"],
            "total_km": data["total_km"],
            "work_order_number": data["work_order_number"],
            "status": data["status"],
            "root_cause": data["root_cause"],
            "work_completed": data["work_completed"],
            "findings": data["findings"],
            "images": data["images"],
            "signature": data["signature"]  # Will be updated by S3-triggered Lambda later
        }

        # $ Upddate the status of the request created status
        table_requests.update_item(
            Key={"id": data["selectedRowId"]},
            UpdateExpression="SET #s = :status, action_id = :action_id",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":status": data["status"],
                ":action_id": item_id
            },
            ConditionExpression="attribute_exists(id)"
        )

        table.put_item(Item=item)

        return _response(200, {"data": item, "presigned_urls": presigned_urls})

    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": "Internal server error"})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": HEADERS,
        "body": json.dumps(body),
    }

# Run the lambda locally with the events.json file to test
# if __name__ == "__main__":
#     with open("event.json") as f:
#         event = json.load(f)

#     result = lambda_handler(event, None)
#     print(json.dumps(result, indent=2))
