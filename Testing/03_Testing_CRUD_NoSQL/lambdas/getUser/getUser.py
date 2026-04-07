# $ This lambda get the user from Cognito or the database, if the user does not exist in the database it will then create the user to be in sync with Cognito.

import json
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timezone, timedelta
import os

# Clients
dynamodb = boto3.resource("dynamodb")
cognito = boto3.client("cognito-idp")
ssm = boto3.client("ssm")

TABLE_NAME = "crud-nosql-app-users-table"

# Fetch user pool id from SSM parameter
USER_POOL_PARAM = os.getenv("USER_POOL_PARAM", "/crud-nosql/cognito")

def get_user_pool_id():
    """Fetch the Cognito User Pool ID from SSM"""
    response = ssm.get_parameter(Name=USER_POOL_PARAM)
    return response["Parameter"]["Value"]

table = dynamodb.Table(TABLE_NAME)
HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With",
    "Access-Control-Allow-Credentials": "true"
}

def to_human_date(iso_string: str) -> str:
    SAST = timezone(timedelta(hours=2))
    dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    return dt.astimezone(SAST).strftime("%d %b %Y, %H:%M")

def lambda_handler(event, context):
    try:
        claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
        user_id = claims.get("sub")

        if not user_id:
            return _response(401, {"message": "Unauthorized"})
        
        # Get userpool id:
        userpool_id = get_user_pool_id()
        
        cognito_username = claims.get("username", user_id)
        response = cognito.admin_get_user(
        UserPoolId=userpool_id,
        Username=cognito_username
        )

        # user cognito status
        status = response["UserStatus"]

        groups = claims.get("cognito:groups")
        if not groups:
            groups = ["admin"]
        elif isinstance(groups, str):
            groups = [groups]

        # Extract Cognito attributes
        email = claims.get("email")
        name = claims.get("name", "")
        family_name = claims.get("family_name", "")

        # Check DB and create user if missing
        result = table.get_item(Key={"id": user_id})
        item = result.get("Item")

        # --- 5. Store user in DynamoDB ---
        now = datetime.now(timezone.utc).isoformat()

        # Create user if it does not exist in database but is avaialble in Cognito
        if not item:
            item = {
                "id": user_id,
                "email": email,
                "name": name,
                "family_name": family_name,
                "username":cognito_username,
                "email_verified": True,
                "status": status,
                "groups": groups if groups else ["admin"],
                "location": "central services",
                "mobile":"",
                "userCreated":to_human_date(now),
                "updatedAt":to_human_date(now)
            }
            table.put_item(Item=item, ConditionExpression="attribute_not_exists(id)")

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
