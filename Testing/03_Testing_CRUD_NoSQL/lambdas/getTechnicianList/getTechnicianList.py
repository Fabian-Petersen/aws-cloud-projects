import json
import os
import boto3
from botocore.exceptions import ClientError

cognito = boto3.client("cognito-idp")

USER_POOL_ID = os.environ["USER_POOL_ID"]
GROUP_NAME = "technician"

def get_attr(user, name):
    for attr in user.get("Attributes", []):
        if attr.get("Name") == name:
            return attr.get("Value", "")
    return ""


def list_technicians():
    technicians = []
    next_token = None

    while True:
        params = {
            "UserPoolId": USER_POOL_ID,
            "GroupName": GROUP_NAME,
        }

        if next_token:
            params["NextToken"] = next_token

        response = cognito.list_users_in_group(**params)

        for user in response.get("Users", []):
            sub = get_attr(user, "sub")
            first_name = get_attr(user, "name")
            family_name = get_attr(user, "family_name")
            email = get_attr(user, "email")

            full_name = f"{first_name} {family_name}".strip()

            if not full_name:
                full_name = email or user.get("Username", "")

            if sub:
                technicians.append({
                    "label": full_name,   # for select display
                    "value": sub,         # for select value
                    "name": full_name,    # send in payload
                    "sub": sub,           # send in payload
                })

        next_token = response.get("NextToken")
        if not next_token:
            break

    return technicians


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "http://localhost:5173",
            "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
            "Access-Control-Allow-Credentials": "true"
        },
        "body": json.dumps(body),
    }

def lambda_handler(event, context):
    http_method = event.get("requestContext", {}).get("http", {}).get("method") \
        or event.get("httpMethod")

    if http_method == "OPTIONS":
        return response(200, {"message": "OK"})

    try:
        technicians = list_technicians()
        return response(200, technicians)

    except ClientError as e:
        print("Cognito error:", e)
        return response(500, {"message": "Failed to fetch technicians"})

    except Exception as e:
        print("Unexpected error:", e)
        return response(500, {"message": "Unexpected server error"})