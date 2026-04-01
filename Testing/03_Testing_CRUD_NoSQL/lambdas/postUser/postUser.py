import json
import boto3
from datetime import datetime, timezone
import os

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("crud-nosql-app-users-table")
cognito = boto3.client("cognito-idp")
ssm = boto3.client("ssm")

# Fetch user pool id from SSM parameter
USER_POOL_PARAM = os.getenv("USER_POOL_PARAM", "/crud-nosql/cognito")

def get_user_pool_id():
    """Fetch the Cognito User Pool ID from SSM"""
    response = ssm.get_parameter(Name=USER_POOL_PARAM)
    return response["Parameter"]["Value"]

def to_human_date(iso_string: str) -> str:
    dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    return dt.strftime("%d %b %Y, %H:%M")

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "DELETE,OPTIONS, POST",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With",
    "Access-Control-Allow-Credentials": "true"
}

def get_cognito_user_by_email(email: str, user_pool_id: str) -> dict | None:
    """
    Returns the Cognito user dict if a user with the given email exists,
    otherwise returns None.
    Uses list_users with an email filter instead of admin_get_user,
    because the username may not match the email.
    """
    result = cognito.list_users(
        UserPoolId=user_pool_id,
        Filter=f'email = "{email}"',
        Limit=1,
    )
    users = result.get("Users", [])
    return users[0] if users else None


def lambda_handler(event, context):
    try:
        # --- 1. Parse and validate input ---
        body = json.loads(event.get("body", "{}"))

        required_fields = ["email", "group", "family_name", "name", "location", "mobile"]
        missing = [f for f in required_fields if not body.get(f)]
        if missing:
            return _response(400, {"error": f"Missing required fields: {', '.join(missing)}"})

        email       = body["email"]
        group       = body["group"]
        family_name = body["family_name"]
        name        = body["name"]
        location    = body["location"]
        mobile      = body["mobile"]

        #  Get the userpool id
        user_pool_id = get_user_pool_id()

        # --- 2. Check if user already exists in Cognito by email ---
        existing_user = get_cognito_user_by_email(email, user_pool_id)
        if existing_user:
            return _response(409, {"error": "User already exists."})
        

        # --- 3. Create user in Cognito ---
        cognito_response = cognito.admin_create_user(
            UserPoolId=user_pool_id,
            Username=email,
            UserAttributes=[
                {"Name": "email",           "Value": email},
                {"Name": "name",            "Value": name},
                {"Name": "family_name",     "Value": family_name},
                {"Name": "email_verified",  "Value": "true"},
            ],
            DesiredDeliveryMediums=["EMAIL"],
        )

        user = cognito_response["User"]

        sub = next(
            attr["Value"]
            for attr in user["Attributes"]
            if attr["Name"] == "sub"
        )
        username = user["Username"]

        # --- 4. Add user to Cognito group ---
        cognito.admin_add_user_to_group(
            UserPoolId=user_pool_id,
            Username=username,
            GroupName=group,
        )

        # --- 5. Store user in DynamoDB ---
        now = datetime.now(timezone.utc).isoformat()

        item = {
            "id":             sub,
            "email":          email,
            "name":           name,
            "family_name":    family_name,
            "username":       username,
            "email_verified": True,
            "status":         "FORCE_CHANGE_PASSWORD",
            "groups":         [group],
            "location":       location,
            "mobile":         mobile,
            "userCreated":    to_human_date(now),
            "updatedAt":      to_human_date(now),
        }

        table.put_item(Item=item)

        return _response(201, {"message": "User created successfully", "user": item})

    except cognito.exceptions.UsernameExistsException:
        return _response(409, {"error": "User already exists."})

    except cognito.exceptions.InvalidParameterException as e:
        return _response(400, {"error": f"Invalid parameter: {str(e)}"})

    except cognito.exceptions.ResourceNotFoundException as e:
        return _response(404, {"error": f"Cognito group or user pool not found: {str(e)}"})

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return _response(500, {"error": "Internal server error."})


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": HEADERS,
        "body": json.dumps(body, default=str),
    }

# --- Local testing ---
if __name__ == "__main__":
    with open("event.json") as f:
        event = json.load(f)

    result = lambda_handler(event, None)
    print(json.dumps(result, indent=2))