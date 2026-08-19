import boto3
import json
from datetime import datetime, timezone, timedelta

# Clients
dynamodb = boto3.resource("dynamodb")
ssm = boto3.client("ssm")

TABLE_NAME = "crud-nosql-app-users-table"

table = dynamodb.Table(TABLE_NAME)

def to_human_date(iso_string: str) -> str:
    SAST = timezone(timedelta(hours=2))
    dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    return dt.astimezone(SAST).strftime("%d %b %Y, %H:%M")

def lambda_handler(event, context):
    """
    Lambda to fetch all users from DynamoDB.
    Can be hooked up to a GET /admin/users route.
    """
    print('event:', event)
    users = []

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

    # Scan DynamoDB table to fetch all users
    response = table.scan()
    for item in response.get("Items", []):
        users.append(item)

    # Handle pagination if there are more items
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        for item in response.get("Items", []):
            users.append(item)

    return _response(200, users, HEADERS)

def _response(status_code, body, headers):
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body),
    }

# --- Local testing using event.json ---
if __name__ == "__main__":
    with open("event.json") as f:
        event = json.load(f)

    result = lambda_handler(event, None)
    print(result["body"])