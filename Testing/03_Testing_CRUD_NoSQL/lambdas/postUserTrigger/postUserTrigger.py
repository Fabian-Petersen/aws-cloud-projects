import json
import boto3
from datetime import datetime, timezone
import os

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("crud-nosql-app-users-table")
cognito = boto3.client("cognito-idp")

USER_POOL_ID = os.environ.get("USER_POOL_ID")

def to_human_date(iso_string: str) -> str:
    dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    return dt.strftime("%d %b %Y, %H:%M")

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "DELETE,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With",
    "Access-Control-Allow-Credentials": "true"
}

def lambda_handler(event, context):
    try:
        # --- 1. Parse and validate input ---
        body = json.loads(event.get("body", "{}"))

        required_fields = ["email", "group", "family_name", "name", "location"]
        missing = [f for f in required_fields if not body.get(f)]
        if missing:
            return response(400, {"error": f"Missing required fields: {', '.join(missing)}"})

        email       = body["email"]
        group       = body["group"]
        family_name = body["family_name"]
        name        = body["name"]
        location    = body["location"]

        # --- 2. Create user in Cognito ---
        cognito_response = cognito.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=email,
            UserAttributes=[
                {"Name": "email",           "Value": email},
                {"Name": "name",            "Value": name},
                {"Name": "family_name",     "Value": family_name},
                {"Name": "email_verified",  "Value": "true"},
            ],
            DesiredDeliveryMediums=["EMAIL"],  # Sends temporary password via email
        )

        user = cognito_response["User"]

        # Extract the Cognito sub from the returned attributes
        sub = next(
            attr["Value"]
            for attr in user["Attributes"]
            if attr["Name"] == "sub"
        )
        username = user["Username"]

        # --- 3. Add user to Cognito group ---
        cognito.admin_add_user_to_group(
            UserPoolId=USER_POOL_ID,
            Username=username,
            GroupName=group,
        )

        # --- 4. Store user in DynamoDB ---
        now = datetime.now(timezone.utc).isoformat()

        item = {
            "id":             sub,
            "email":          email,
            "name":           name,
            "family_name":    family_name,
            "username":       username,
            "email_verified": True,
            "status":         "FORCE_CHANGE_PASSWORD",  # Default Cognito status for new admin-created users
            "groups":         [group],
            "location":       location,
            "userCreated":    to_human_date(now),
            "updatedAt":      to_human_date(now),
        }

        table.put_item(Item=item)

        return response(201, {"message": "User created successfully", "user": item})

    except cognito.exceptions.UsernameExistsException:
        return response(409, {"error": "A user with this email already exists."})

    except cognito.exceptions.InvalidParameterException as e:
        return response(400, {"error": f"Invalid parameter: {str(e)}"})

    except cognito.exceptions.ResourceNotFoundException as e:
        return response(404, {"error": f"Cognito group or user pool not found: {str(e)}"})

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return response(500, {"error": "Internal server error."})


def response(status_code: int, body: dict) -> dict:
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