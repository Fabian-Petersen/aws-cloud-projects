import json
import boto3

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

TABLE_NAME = "crud-nosql-app-maintenance-action-table"
BUCKET_NAME = "crud-nosql-app-images"

table = dynamodb.Table(TABLE_NAME)

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With",
    "Access-Control-Allow-Credentials": "true"
}

def lambda_handler(event, context):
    try:
        request_uuid = event.get("pathParameters", {}).get("id")
        if not request_uuid:
            return _response(400, {"message": "id (UUID) is required"})

        # 1. Fetch item to get image metadata
        response = table.get_item(
            Key={"id": request_uuid}
        )

        item = response.get("Item")
        if not item:
            return _response(404, {"message": "Item not found"})

        # 2. Delete images from S3
        images = item.get("images", [])

        for image in images:
            s3_key = image.get("key")
            if s3_key:
                s3.delete_object(
                    Bucket=BUCKET_NAME,
                    Key=s3_key
                )

        # 3. Delete DynamoDB item
        table.delete_item(
            Key={"id": request_uuid}
        )

        return _response(200, {"message": "Request and images deleted successfully"})

    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": "Internal server error"})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": HEADERS,
        "body": json.dumps(body),
    }