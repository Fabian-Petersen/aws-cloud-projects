import boto3
import json
import os

# $ Clients
cognito = boto3.client("cognito-idp")
ssm = boto3.client("ssm")

# $ Fetch user pool id from SSM parameter
USER_POOL_PARAM = os.getenv("USER_POOL_PARAM", "/crud-nosql/cognito")
def get_user_pool_id():
    response = ssm.get_parameter(Name=USER_POOL_PARAM)
    return response["Parameter"]["Value"]

def lambda_handler(event, context):
    """
    Expects event to be a dict like:
    {
      "username": "test@gmail.com",
      "group": "manager",
      "attributes": {
        "email": "test@gmail.com",
        "email_verified": "true",
        "family_name": "petersen",
        "name": "fabian"
      }
    }
    """
    user_pool_id = get_user_pool_id()

    username = event["username"]
    group = event["group"]
    attributes = event.get("attributes", {})

    # $ Prepare Cognito UserAttributes list
    user_attributes = [{"Name": k, "Value": v} for k, v in attributes.items()]

    # $ Create user
    cognito.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=user_attributes,
        MessageAction="SUPPRESS"  # Avoid sending email if you want custom flow
    )

    # $ Add user to group
    cognito.admin_add_user_to_group(
        UserPoolId=user_pool_id,
        Username=username,
        GroupName=group
    )

    return {
        "status": "success",
        "username": username,
        "group": group
    }

# --- Local testing ---
if __name__ == "__main__":
    os.environ["USER_POOL_PARAM"] = "/crud-nosql/cognito/cognito_user_pool_id"

    with open("event.json") as f:
        event = json.load(f)

    result = lambda_handler(event, None)
    print(json.dumps(result, indent=2))