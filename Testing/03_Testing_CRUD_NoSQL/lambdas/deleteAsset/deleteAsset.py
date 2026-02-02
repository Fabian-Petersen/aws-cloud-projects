import json
import boto3

TABLE_NAME = "crud-nosql-app-assets-table"
BUCKET_NAME = "crud-nosql-app-images"

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")
table = dynamodb.Table(TABLE_NAME)

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "DELETE,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
}

def lambda_handler(event, context):
    try:
        item_id = event.get("pathParameters", {}).get("id")
        if not item_id:
            return _response(400, {"message": "id (UUID) is required"})

        #$ 1. Get item first (to confirm existence)
        item_response = table.get_item(Key={"id": item_id})
        if "Item" not in item_response:
            return _response(404, {"message": "Item not found"})

        #$ 2. Delete all images in S3 folder assets/{item_id}/
        prefix = f"assets/{item_id}/"
        objects = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)

        if "Contents" in objects:
            delete_payload = {
                "Objects": [{"Key": obj["Key"]} for obj in objects["Contents"]]
            }
            s3.delete_objects(Bucket=BUCKET_NAME, Delete=delete_payload)

        #$ 3. Delete DynamoDB item
        table.delete_item(Key={"id": item_id})

        return _response(200, {"message": "Asset and images deleted successfully"})

    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": "Internal server error"})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": HEADERS,
        "body": json.dumps(body),
    }