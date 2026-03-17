# $ This lambda return all the requests pending approval

import json
import boto3
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.conditions import Attr
from datetime import datetime

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("crud-nosql-app-maintenance-request-table")

# $ Change the date format in the database to readible for humans
def to_human_date(iso_string: str) -> str:
    dt = datetime.fromisoformat(iso_string)
    return dt.strftime("%d %b %Y, %H:%M")

# $ Get the User Groups from the claims
def parse_groups(groups_claim):
    if not groups_claim:
        return []

    if isinstance(groups_claim, list):
        return [str(group).lower() for group in groups_claim]

    if isinstance(groups_claim, str):
        # Handle JSON array string or simple comma-separated/string values
        try:
            parsed = json.loads(groups_claim)
            if isinstance(parsed, list):
                return [str(group).lower() for group in parsed]
        except Exception:
            pass

        return [group.strip().lower() for group in groups_claim.split(",")]

    return []

# $ Return jobs that are approved using the status GSI
def query_all_approved(**kwargs):
    items = []
    response = table.query(
        IndexName="StatusJobCreatedIndex",
        KeyConditionExpression=Key("status").eq("In Progress"),
        ScanIndexForward=False,  # newest first
        **kwargs
    )
    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = table.query(
            IndexName="StatusJobCreatedIndex",
            KeyConditionExpression=Key("status").eq("In Progress"),
            ExclusiveStartKey=response["LastEvaluatedKey"],
            ScanIndexForward=False, # use to sort by jobCreated last -> first
            **kwargs
        )
        items.extend(response.get("Items", []))

    return items
def lambda_handler(event, context):
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    groups = parse_groups(claims.get("cognito:groups"))
    user_sub = claims.get("sub")

    # $ Grab the Origin header from the incoming request
    headers = event.get("headers") or {}
    origin = headers.get("origin") or headers.get("Origin") or ""

    allowedOrigins = [
    'https://www.crud-nosql.app.fabian-portfolio.net',
    'https://crud-nosql.app.fabian-portfolio.net',
    'http://localhost:5173'
    ]

    # $ Only allow known origins
    allowedOrigin = origin if origin in allowedOrigins else ""
    
    HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": allowedOrigin,
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Credentials": "true"
        }

    method = (
        event.get("httpMethod")
        or event.get("requestContext", {}).get("http", {}).get("method")
    )

    if method == "OPTIONS":
        print("OPTIONS request...")
        return _response(200, {"message": "Success"}, HEADERS)
        
    # $ Admin can see all completed actions and technician what he submitted 
    try:
        is_admin_users= any(group in ["admin", "technician", "user", "contractor"] for group in groups)

        if is_admin_users:
            items = query_all_approved()
        else:
            if not user_sub:
                return _response(403, {"message": "User sub not found in token"}, HEADERS)

            # Assumes each item stores the creator's sub in a field called "request_sub"
            items = query_all_approved(FilterExpression=Attr("request_sub").eq(user_sub))

        for item in items:
            if "jobCreated" in item:
                item["jobCreated"] = to_human_date(item["jobCreated"])

        return _response(200, items, HEADERS)

    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": "Internal server error"}, HEADERS)


def _response(status_code, body, headers):
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body),
    }
