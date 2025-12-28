import json
import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("crud-nosql-app-assets-table")

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "DELETE,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
}

def lambda_handler(event, context):
    try:
        # UUID comes from path parameters
        asset_uuid = event.get("pathParameters", {}).get("id")
        if not asset_uuid:
            return _response(400, {"message": "id (UUID) is required"})

        # Delete the item using its primary key
        table.delete_item(
            Key={
                "id": asset_uuid  # replace 'id' with your actual primary key name
            }
        )

        return _response(200, {"message": "Asset deleted successfully"})

    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": "Internal server error"})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": HEADERS,
        "body": json.dumps(body),
    }