import boto3
import os

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
    user_pool_id = get_user_pool_id()
    print("event"), event