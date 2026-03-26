import json
import boto3
from botocore.exceptions import ClientError

# Clients
dynamodb = boto3.resource("dynamodb")
TABLE_NAME = "crud-nosql-app-users-table"

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
        user_id = event.get("pathParameters", {}).get("userId")
        if not user_id:
            return _response(400, {"message": "userId is required"})

        # Fetch user from DynamoDB — single source of truth for user data
        # DynamoDB holds all schema fields including those synced from Cognito:
        # id, email, name, family_name, username, email_verified,
        # status, group, location, userCreated, updatedAt
        result = table.get_item(
            Key={"pk": f"USER#{user_id}"}
        )

        item = result.get("Item")
        if not item:
            return _response(404, {"message": "User not found"})

        # Strip the internal DynamoDB pk before returning
        item.pop("pk", None)

        return _response(200, item)

    except ClientError as e:
        print("AWS ClientError:", e)
        return _response(500, {"message": f"AWS error: {e.response['Error']['Message']}"})

    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": "Internal server error"})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": HEADERS,
        "body": json.dumps(body),
    }