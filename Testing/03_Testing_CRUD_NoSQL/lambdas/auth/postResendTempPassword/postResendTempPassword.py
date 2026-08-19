import json
import boto3
import os

client = boto3.client("cognito-idp")
ssm = boto3.client("ssm")
dynamodb = boto3.resource("dynamodb")

TABLE_NAME = "crud-nosql-app-users-table"
table = dynamodb.Table(TABLE_NAME)

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With",
    "Access-Control-Allow-Credentials": "true"
}

# Fetch user pool id from SSM parameter
USER_POOL_PARAM = os.getenv("USER_POOL_PARAM", "/crud-nosql/cognito")

def get_user_pool_id():
    """Fetch the Cognito User Pool ID from SSM"""
    response = ssm.get_parameter(Name=USER_POOL_PARAM)
    return response["Parameter"]["Value"]

def lambda_handler(event, context):
    # $ Grab the Origin header from the incoming request
    headers = event.get("headers") or {}
    origin = headers.get("origin") or headers.get("Origin") or ""

    allowedOrigins = [
    'https://www.crud-nosql.app.fabian-portfolio.net',
    'https://crud-nosql.app.fabian-portfolio.net',
    'http://localhost:5173'
    ]

    # $ Only allow known origins
    allowedOrigin = origin if origin in allowedOrigins else ""
    
    HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": allowedOrigin,
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Credentials": "true"
        }

    method = (
        event.get("httpMethod")
        or event.get("requestContext", {}).get("http", {}).get("method")
    )

    if method == "OPTIONS":
        print("OPTIONS request...")
        return _response(200, {"message": "Success"}, HEADERS)
    
    try:
        user_id = event.get("pathParameters", {}).get("id")
        if not user_id:
            return _response(400, {"message": "user id is required"}, HEADERS)
        
        # Fetch user from DynamoDB — single source of truth for user data
        # DynamoDB holds all schema fields including those synced from Cognito:
        # id, email, name, family_name, username, email_verified,
        # status, group, location, userCreated, updatedAt
        result = table.get_item(
            Key={"id": user_id}
        )

        item = result.get("Item")
        if not item:
            return _response(404, {"message": "User not found"}, HEADERS)

        email = item.get("email")
        if not email:
            return _response(404, {"message": "User email not found"}, HEADERS)

        #  Get the userpool id
        user_pool_id = get_user_pool_id()
        client.admin_create_user(
            UserPoolId=user_pool_id,
            Username=email,
            MessageAction="RESEND"
        )

        return _response(200, {"message": "Temporary password resent"}, HEADERS)

    except client.exceptions.UserNotFoundException:
        return _response(401, {"message": "User not found"}, HEADERS)

    except Exception as e:
        return _response(500, {"message":str(e)}, HEADERS)

    
def _response(status_code: int, body: dict, headers: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body, default=str),
    }

# --- Local testing ---
if __name__ == "__main__":
    with open("event.json") as f:
        event = json.load(f)

    result = lambda_handler(event, None)
    print(json.dumps(result, indent=2))