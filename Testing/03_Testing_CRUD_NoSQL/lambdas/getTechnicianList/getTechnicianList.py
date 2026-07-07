import json
import os
import boto3
from decimal import Decimal
from botocore.exceptions import ClientError

cognito = boto3.client("cognito-idp")

USER_POOL_ID = os.environ["USER_POOL_ID"]
GROUP_NAME = "technician"


def get_attr(user, name):
    for attr in user.get("Attributes", []):
        if attr.get("Name") == name:
            return attr.get("Value", "")
    return ""

# ----------------------------
# Decimal serializer for DynamoDB types in JSON responses
# ----------------------------


def decimal_serializer(obj):
    """
    Custom JSON serializer for handling DynamoDB Decimal types.

    Args:
        obj: Object to serialize.

    Returns:
        int | float: Converted numeric value.

    Raises:
        TypeError: If object type is not supported.
    """
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    raise TypeError


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


def handle_request_metadata(event):
    """
    Extract HTTP method and construct CORS headers based on request origin.

    Args:
        event (dict): Lambda event payload.

    Returns:
        tuple:
            method (str): HTTP method (GET, POST, OPTIONS, etc.)
            response_headers (dict): CORS-enabled response headers.
    """
    headers = event.get("headers") or {}
    origin = headers.get("origin") or headers.get("Origin") or ""

    allowed_origins = [
        "https://www.crud-nosql.app.fabian-portfolio.net",
        "https://crud-nosql.app.fabian-portfolio.net",
        "http://localhost:5173",
    ]

    allowed_origin = origin if origin in allowed_origins else ""

    response_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": allowed_origin,
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Credentials": "true",
    }

    method = (
        event.get("httpMethod")
        or event.get("requestContext", {}).get("http", {}).get("method")
    )

    return method, response_headers


def handle_options_request(method, headers):
    """
    Handle CORS preflight (OPTIONS) requests.

    Args:
        method (str): HTTP method.
        headers (dict): Response headers.

    Returns:
        dict | None: HTTP response if OPTIONS request, otherwise None.
    """
    if method == "OPTIONS":
        return _response(200, {"message": "Success"}, headers)
    return None


def lambda_handler(event, context):
    # CORS
    method, HEADERS = handle_request_metadata(event)

    options_response = handle_options_request(method, HEADERS)
    if options_response:
        return options_response

    try:
        technicians = list_technicians()
        return _response(200, technicians, HEADERS)

    except ClientError as e:
        print("Cognito error:", e)
        return _response(500, {"message": "Failed to fetch technicians"}, HEADERS)

    except Exception as e:
        print("Unexpected error:", e)
        return _response(500, {"message": "Unexpected server error"}, HEADERS)


# ----------------------------
# Response helper
# ----------------------------
def _response(status_code, body, headers):
    """
    Construct a standard API Gateway HTTP response.

    Args:
        status_code (int): HTTP status code.
        body (dict | list): Response payload.
        headers (dict): HTTP headers.

    Returns:
        dict: Formatted response object.
    """
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body, default=decimal_serializer),
    }
