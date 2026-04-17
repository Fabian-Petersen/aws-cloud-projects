"""
This function returns all the jobs in the maintenance request table. Admins and technicians can see all jobs, while regular users only see their own jobs. The function also supports filtering by job status using a GSI for efficient queries. CORS headers are dynamically set based on the request origin, and dates are formatted for human readability in SAST. The function handles OPTIONS requests for CORS preflight and includes robust error handling for missing user information or database issues.

"""

import json
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Key
from datetime import datetime, timezone, timedelta

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("crud-nosql-app-maintenance-request-table")

# ----------------------------
# Date formatting in SAST for human readability 
# ----------------------------
def to_human_date(iso_string: str) -> str:
    """
    Convert an ISO 8601 timestamp string to a human-readable date in SAST.

    Args:
        iso_string (str): ISO formatted datetime string (e.g., "2024-01-01T12:00:00Z").

    Returns:
        str: Formatted date string (e.g., "01 Jan 2024, 14:00").
    """
    SAST = timezone(timedelta(hours=2))
    dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    return dt.astimezone(SAST).strftime("%d %b %Y, %H:%M")

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

# ----------------------------
# Cognito groups parser for flexible group claim formats
# ----------------------------
def parse_groups(groups_claim):
    if not groups_claim:
        return []

    if isinstance(groups_claim, list):
        return [str(group).lower() for group in groups_claim]

    if isinstance(groups_claim, str):
        try:
            parsed = json.loads(groups_claim)
            if isinstance(parsed, list):
                return [str(group).lower() for group in parsed]
        except Exception:
            pass

        return [group.strip().lower() for group in groups_claim.split(",")]

    return []


# ----------------------------
# Scan fallback (no filters)
# ----------------------------
def scan_all():
    items = []
    response = table.scan()
    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = table.scan(
            ExclusiveStartKey=response["LastEvaluatedKey"]
        )
        items.extend(response.get("Items", []))

    return items


# ----------------------------
# GSI query (status-based)
# ----------------------------
def query_by_status(status):
    items = []

    response = table.query(
        IndexName="StatusIndex",
        KeyConditionExpression=Key("status").eq(status)
    )

    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = table.query(
            IndexName="StatusIndex",
            KeyConditionExpression=Key("status").eq(status),
            ExclusiveStartKey=response["LastEvaluatedKey"]
        )
        items.extend(response.get("Items", []))

    return items

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


# ----------------------------
# Lambda handler
# ----------------------------
def lambda_handler(event, context):

    # Query params
    query_params = event.get("queryStringParameters") or {}
    status = query_params.get("status")

    # Auth claims
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    groups = parse_groups(claims.get("cognito:groups"))
    user_sub = claims.get("sub")

    # CORS
    method, HEADERS = handle_request_metadata(event)

    options_response = handle_options_request(method, HEADERS)
    if options_response:
        return options_response

    try:
        is_admin_or_technician = any(group in ["admin", "technician"] for group in groups)

        # ----------------------------
        # DATA FETCH LOGIC
        # ----------------------------

        if is_admin_or_technician:
            # ✅ USE GSI IF STATUS EXISTS
            if status:
                items = query_by_status(status)
            else:
                items = scan_all()

        else:
            # Non-admin users only see their own jobs
            if not user_sub:
                return _response(403, {"message": "User sub not found in token"}, HEADERS)

            if status:
                # GSI + user filter fallback (no composite index)
                items = query_by_status(status)
                items = [item for item in items if item.get("request_sub") == user_sub]
            else:
                items = scan_all()
                items = [item for item in items if item.get("request_sub") == user_sub]

        # ----------------------------
        # Format dates
        # ----------------------------
        for item in items:
            if "jobCreated" in item:
                item["jobCreated"] = to_human_date(item["jobCreated"])

        return _response(200, items, HEADERS)

    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": "Internal server error"}, HEADERS)


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



# import json
# import boto3
# # from boto3.dynamodb.conditions import Key
# from boto3.dynamodb.conditions import Attr
# from datetime import datetime, timezone, timedelta

# dynamodb = boto3.resource("dynamodb")
# table = dynamodb.Table("crud-nosql-app-maintenance-request-table")

# # $ Change the date format in the database to readible for humans
# def to_human_date(iso_string: str) -> str:
#     SAST = timezone(timedelta(hours=2))
#     dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
#     return dt.astimezone(SAST).strftime("%d %b %Y, %H:%M")

# # $ Get the User Groups from the claims
# def parse_groups(groups_claim):
#     if not groups_claim:
#         return []

#     if isinstance(groups_claim, list):
#         return [str(group).lower() for group in groups_claim]

#     if isinstance(groups_claim, str):
#         # Handle JSON array string or simple comma-separated/string values
#         try:
#             parsed = json.loads(groups_claim)
#             if isinstance(parsed, list):
#                 return [str(group).lower() for group in parsed]
#         except Exception:
#             pass

#         return [group.strip().lower() for group in groups_claim.split(",")]

#     return []


# def scan_all(**kwargs):
#     items = []
#     response = table.scan(**kwargs)
#     items.extend(response.get("Items", []))

#     while "LastEvaluatedKey" in response:
#         response = table.scan(
#             ExclusiveStartKey=response["LastEvaluatedKey"],
#             **kwargs
#         )
#         items.extend(response.get("Items", []))

#     return items
    
# def lambda_handler(event, context):
#     claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
#     groups = parse_groups(claims.get("cognito:groups"))
#     user_sub = claims.get("sub")

#     # $ Grab the Origin header from the incoming request
#     headers = event.get("headers") or {}
#     origin = headers.get("origin") or headers.get("Origin") or ""

#     allowedOrigins = [
#     'https://www.crud-nosql.app.fabian-portfolio.net',
#     'https://crud-nosql.app.fabian-portfolio.net',
#     'http://localhost:5173',
#     'http://localhost:8085' # swagger api testing
#     ]

#     # $ Only allow known origins
#     allowedOrigin = origin if origin in allowedOrigins else ""
    
#     HEADERS = {
#     "Content-Type": "application/json",
#     "Access-Control-Allow-Origin": allowedOrigin,
#     "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
#     "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
#     "Access-Control-Allow-Credentials": "true"
#         }

#     method = (
#         event.get("httpMethod")
#         or event.get("requestContext", {}).get("http", {}).get("method")
#     )

#     if method == "OPTIONS":
#         print("OPTIONS request...")
#         return _response(200, {"message": "Success"}, HEADERS)
        
#     # $ Admin can see all completed actions and technician what he submitted 
#     try:
#         is_admin_or_technician = any(group in ["admin", "technician"] for group in groups)

#         if is_admin_or_technician:
#             items = scan_all()
#         else:
#             if not user_sub:
#                 return _response(403, {"message": "User sub not found in token"}, HEADERS)

#             # Assumes each item stores the creator's sub in a field called "request_sub"
#             items = scan_all(FilterExpression=Attr("request_sub").eq(user_sub))

#         for item in items:
#             if "jobCreated" in item:
#                 item["jobCreated"] = to_human_date(item["jobCreated"])

#         return _response(200, items, HEADERS)

#     except Exception as exc:
#         print("Error:", exc)
#         return _response(500, {"message": "Internal server error"}, HEADERS)


# def _response(status_code, body, headers):
#     return {
#         "statusCode": status_code,
#         "headers": headers,
#         "body": json.dumps(body),
#     }
