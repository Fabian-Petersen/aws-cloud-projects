import json
import boto3
import os
from datetime import datetime, timezone
from botocore.exceptions import ClientError

# Clients
dynamodb = boto3.resource("dynamodb")
cognito = boto3.client("cognito-idp")
ssm = boto3.client("ssm")

TABLE_NAME = "crud-nosql-app-users-table"
USER_POOL_PARAM = os.getenv("USER_POOL_PARAM", "/crud-nosql/cognito")

table = dynamodb.Table(TABLE_NAME)

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "PUT,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With",
    "Access-Control-Allow-Credentials": "true"
}

# Schema reference:
# id, email, name, family_name, username, email_verified, status, group, location, userCreated, updatedAt

# Synced to Cognito AND DynamoDB
COGNITO_ATTRIBUTES = {"email", "name", "family_name"}

# Stored in DynamoDB only — not in Cognito
DYNAMO_ONLY_FIELDS = {"location"}

# Read-only — never updatable via this endpoint
READ_ONLY_FIELDS = {"id", "username", "email_verified", "status", "userCreated", "updatedAt"}

# All fields the caller is allowed to send
ALLOWED_FIELDS = {"email", "name", "family_name", "group", "location"}


def get_user_pool_id():
    """Fetch the Cognito User Pool ID from SSM"""
    response = ssm.get_parameter(Name=USER_POOL_PARAM)
    return response["Parameter"]["Value"]


def update_cognito_attributes(user_pool_id, user_id, updates):
    """Update standard Cognito user attributes (email, name, family_name)"""
    cognito_updates = [
        {"Name": key, "Value": str(value)}
        for key, value in updates.items()
        if key in COGNITO_ATTRIBUTES
    ]

    if cognito_updates:
        cognito.admin_update_user_attributes(
            UserPoolId=user_pool_id,
            Username=user_id,
            UserAttributes=cognito_updates
        )


def update_cognito_group(user_pool_id, user_id, new_group, current_group):
    """Move user to a new Cognito group, removing them from the current one"""
    if current_group and current_group != new_group:
        cognito.admin_remove_user_from_group(
            UserPoolId=user_pool_id,
            Username=user_id,
            GroupName=current_group
        )

    cognito.admin_add_user_to_group(
        UserPoolId=user_pool_id,
        Username=user_id,
        GroupName=new_group
    )


def update_dynamo(user_id, updates):
    """
    Dynamically build and execute a DynamoDB UpdateItem expression.
    Always sets updatedAt to the current UTC timestamp.
    """
    updates["updatedAt"] = datetime.now(timezone.utc).isoformat()

    expression_parts = []
    expression_names = {}
    expression_values = {}

    for key, value in updates.items():
        safe_key = f"#attr_{key}"
        val_key = f":val_{key}"
        expression_parts.append(f"{safe_key} = {val_key}")
        expression_names[safe_key] = key
        expression_values[val_key] = value

    update_expression = "SET " + ", ".join(expression_parts)

    table.update_item(
        Key={"pk": f"USER#{user_id}"},
        UpdateExpression=update_expression,
        ExpressionAttributeNames=expression_names,
        ExpressionAttributeValues=expression_values,
    )


def lambda_handler(event, context):
    try:
        user_id = event.get("pathParameters", {}).get("userId")
        if not user_id:
            return _response(400, {"message": "userId is required"})

        body = json.loads(event.get("body") or "{}")
        if not body:
            return _response(400, {"message": "Request body is required"})

        # Reject read-only fields
        readonly_violations = set(body.keys()) & READ_ONLY_FIELDS
        if readonly_violations:
            return _response(400, {
                "message": f"Fields are read-only and cannot be updated: {', '.join(readonly_violations)}"
            })

        # Reject unknown fields not in schema
        unknown_fields = set(body.keys()) - ALLOWED_FIELDS
        if unknown_fields:
            return _response(400, {
                "message": f"Unknown fields: {', '.join(unknown_fields)}"
            })

        # 1. Fetch User Pool ID from SSM
        user_pool_id = get_user_pool_id()

        # 2. Verify user exists in DynamoDB
        existing = table.get_item(Key={"pk": f"USER#{user_id}"})
        if not existing.get("Item"):
            return _response(404, {"message": "User not found"})

        current_item = existing["Item"]

        # 3. Update Cognito standard attributes (email, name, family_name)
        update_cognito_attributes(user_pool_id, user_id, body)

        # 4. Handle group change in Cognito (DynamoDB updated in step 5)
        new_group = body.get("group")
        if new_group:
            current_group = current_item.get("group")
            update_cognito_group(user_pool_id, user_id, new_group, current_group)

        # 5. Update DynamoDB with all fields + auto-set updatedAt
        update_dynamo(user_id, body)

        return _response(200, {"message": "User updated successfully"})

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        print("AWS ClientError:", e)

        if error_code == "UserNotFoundException":
            return _response(404, {"message": "User not found in Cognito"})

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