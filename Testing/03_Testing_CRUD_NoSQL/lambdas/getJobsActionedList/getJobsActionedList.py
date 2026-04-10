"""
This function returns all the jobs actioned by a techncian or contractor specific to the user that is logged in i.e. a technician can only see the jobs he actioned. Admin users will see all items

"""
import json
import boto3
from boto3.dynamodb.conditions import Attr
from datetime import datetime, timezone, timedelta

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("crud-nosql-app-maintenance-action-table")
TABLE_NAME_REQUESTS = "crud-nosql-app-maintenance-request-table"
table_requests = dynamodb.Table(TABLE_NAME_REQUESTS)

# Change the date format in the database to readible for humans
def to_human_date(iso_string: str) -> str:
    SAST = timezone(timedelta(hours=2))
    dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    return dt.astimezone(SAST).strftime("%d %b %Y, %H:%M")

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

def scan_all(**kwargs):
    items = []
    response = table.scan(**kwargs)
    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = table.scan(
            ExclusiveStartKey=response["LastEvaluatedKey"],
            **kwargs
        )
        items.extend(response.get("Items", []))

    return items
    
def lambda_handler(event, context):
# $ Get the user from the event
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    groups = parse_groups(claims.get("cognito:groups"))
    user_sub = claims.get("sub")

    #Grab the Origin header from the incoming request
    headers = event.get("headers") or {}
    origin = headers.get("origin") or headers.get("Origin") or ""
    
    allowedOrigins = [
        'https://www.crud-nosql.app.fabian-portfolio.net',
        'https://crud-nosql.app.fabian-portfolio.net',
        'http://localhost:5173'
        ]

    # Only allow known origins
    allowedOrigin = origin if origin in allowedOrigins else ""

    HEADERS = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": allowedOrigin,
        "Access-Control-Allow-Methods": "GET,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With",
        "Access-Control-Allow-Credentials": "true"
    }

    method = (
        event.get("httpMethod")
        or event.get("requestContext", {}).get("http", {}).get("method")
        )

    if method == "OPTIONS":
        return _response(200, {"message": "Success"}, HEADERS)

    try:
        # is_admin_or_technicians = any(group in ["admin", "technician", "contractor"] for group in groups)

        is_admin = "admin" in groups
        if is_admin:
            items = scan_all()
        else:
            if not user_sub:
                return _response(403, {"message": "User sub not found in token"}, HEADERS)

            # Assumes each item stores the creator's sub in a field called "action_sub"
            items = scan_all(FilterExpression=Attr("action_sub").eq(user_sub))

        for item in items:
            if "actionCreated" in item:
                item["actionCreated"] = to_human_date(item["actionCreated"])

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


    # try:
    #     response = table.scan()  # TEMP: returns all items
    #     items = response.get("Items", [])

    #     for item in items:
    #         if "createdAt" in item and item["createdAt"]:
    #             item["createdAt"] = to_human_date(item["createdAt"])

    #         if "completed_at" in item and item["completed_at"]:
    #             item["completed_at"] = to_human_date(item["completed_at"])

    #     return _response(200, response.get("Items", []))

    # except Exception as exc:
    #     print("Error:", exc)
    #     return _response(500, {"message": "Internal server error"})


    # def _response(status_code, body):
    #     return {
    #         "statusCode": status_code,
    #         "headers": HEADERS,
    #         "body": json.dumps(body),
    #     }
