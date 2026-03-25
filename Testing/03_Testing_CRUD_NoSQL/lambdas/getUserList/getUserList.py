import boto3
import os
import json

# Clients
cognito = boto3.client("cognito-idp")
ssm = boto3.client("ssm")

# Fetch user pool id from SSM parameter
USER_POOL_PARAM = os.getenv("USER_POOL_PARAM", "/crud-nosql/cognito")

def get_user_pool_id():
    """Fetch the Cognito User Pool ID from SSM"""
    response = ssm.get_parameter(Name=USER_POOL_PARAM)
    return response["Parameter"]["Value"]

def lambda_handler(event, context):
    """
    Lambda to fetch all users from the Cognito User Pool.
    Can be hooked up to a GET /admin/users route.
    """
    user_pool_id = get_user_pool_id()
    print('userpool:', user_pool_id)
    users = []
    pagination_token = None

    while True:
        if pagination_token:
            response = cognito.list_users(
                UserPoolId=user_pool_id,
                PaginationToken=pagination_token,
                Limit=60  # max allowed per request
            )
        else:
            response = cognito.list_users(
                UserPoolId=user_pool_id,
                Limit=60
            )

        for user in response.get("Users", []):
            user_info = {
                "username": user.get("Username"),
                "attributes": {attr["Name"]: attr["Value"] for attr in user.get("Attributes", [])},
                "status": user.get("UserStatus")
            }
            users.append(user_info)

        pagination_token = response.get("PaginationToken")
        if not pagination_token:
            break

    return {
        "statusCode": 200,
        "body": json.dumps(users, indent=2)
    }

# --- Local testing using event.json ---
if __name__ == "__main__":
    with open("event.json") as f:
        event = json.load(f)

    result = lambda_handler(event, None)
    print(result["body"])