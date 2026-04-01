import json
import boto3
import os
from botocore.exceptions import ClientError

# Clients
dynamodb = boto3.resource("dynamodb")
cognito = boto3.client("cognito-idp")
ssm = boto3.client("ssm")

TABLE_NAME = "crud-nosql-app-users-table"
USER_POOL_ID = "your-user-pool-id"

table = dynamodb.Table(TABLE_NAME)

# Fetch user pool id from SSM parameter
USER_POOL_PARAM = os.getenv("USER_POOL_PARAM", "/crud-nosql/cognito")

def get_user_pool_id():
    """Fetch the Cognito User Pool ID from SSM"""
    response = ssm.get_parameter(Name=USER_POOL_PARAM)
    return response["Parameter"]["Value"]

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "DELETE,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With",
    "Access-Control-Allow-Credentials": "true"
}

def lambda_handler(event, context):
    try:
        user_id = event.get("pathParameters", {}).get("id")
        if not user_id:
            return _response(400, {"message": "userId is required"})

        # 1. Check user exists in DynamoDB
        response = table.get_item(
            Key={"id": user_id}
        )
        #  Get the userpool id
        user_pool_id = get_user_pool_id()

        item = response.get("Item")
        if not item:
            return _response(404, {"message": "User not found"})

        # 2. Delete from Cognito
        try:
            cognito.admin_delete_user(
                UserPoolId=user_pool_id,
                Username=user_id
            )
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "UserNotFoundException":
                # User already gone from Cognito — still clean up DynamoDB
                print(f"User {user_id} not found in Cognito, continuing with DynamoDB delete")
            else:
                raise e

        # 3. Delete from DynamoDB
        table.delete_item(
            Key={"id": user_id}
        )

        return _response(200, {"message": "User deleted successfully"})

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