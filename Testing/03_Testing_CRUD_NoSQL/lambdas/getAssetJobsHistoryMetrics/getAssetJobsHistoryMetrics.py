import boto3
import json
from decimal import Decimal
from boto3.dynamodb.conditions import Key

# ======================================================================================
# DynamoDB
# ======================================================================================

dynamodb = boto3.resource("dynamodb")

jobs_table = dynamodb.Table("crud-nosql-app-maintenance-request-table")
users_table = dynamodb.Table("crud-nosql-app-users-table")

# ======================================================================================
# JSON Encoder
# ======================================================================================


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


# ======================================================================================
# Helpers
# ======================================================================================

def _response(status_code, body, headers):
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body, cls=DecimalEncoder),
    }


FULL_ACCESS_GROUPS = {"admin", "technician"}


def parse_groups(groups_claim):
    if not groups_claim:
        return []

    if isinstance(groups_claim, list):
        return [str(g).lower() for g in groups_claim]

    return [g.strip().lower() for g in groups_claim.split(",")]


def get_user_by_sub(user_sub):
    if not user_sub:
        return None

    return users_table.get_item(Key={"id": user_sub}).get("Item")


def get_user_scope(groups, claims):

    if FULL_ACCESS_GROUPS.intersection(set(groups)):
        return {"full_access": True, "location": None}

    user = get_user_by_sub(claims.get("sub"))

    if not user:
        return {"full_access": False, "location": None}

    return {
        "full_access": False,
        "location": (user.get("location") or "").lower()
    }


# ======================================================================================
# JOB HISTORY QUERY (IMPORTANT PART)
# ======================================================================================

def get_asset_history(asset_id):

    items = []

    response = jobs_table.query(
        IndexName="AssetIdIndex",   # <-- REQUIRED GSI
        KeyConditionExpression=Key("assetID").eq(asset_id)
    )

    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = jobs_table.query(
            IndexName="AssetIdIndex",
            KeyConditionExpression=boto3.Key("assetID").eq(asset_id),
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))

    return items


# ======================================================================================
# FILTER (manager scope)
# ======================================================================================

def filter_by_location(jobs, location):

    if not location:
        return []

    return [
        j for j in jobs
        if (j.get("location") or "").lower() == location
    ]


# ======================================================================================
# Lambda Handler
# ======================================================================================

def lambda_handler(event, context):

    claims = event.get("requestContext", {}).get(
        "authorizer", {}).get("claims", {})
    print("claims:", claims)

    groups = parse_groups(claims.get("cognito:groups"))

    print("event:", event)

    scope = get_user_scope(groups, claims)

    print("scope:", scope)

    headers = event.get("headers") or {}
    origin = headers.get("origin") or headers.get("Origin") or ""

    allowed_origins = [
        "https://www.crud-nosql.app.fabian-portfolio.net",
        "https://crud-nosql.app.fabian-portfolio.net",
        "http://localhost:5173",
    ]

    HEADERS = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": origin if origin in allowed_origins else "",
        "Access-Control-Allow-Methods": "GET,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Credentials": "true",
    }

    method = event.get("httpMethod") or event.get(
        "requestContext", {}).get("http", {}).get("method")

    if method == "OPTIONS":
        return _response(200, {"message": "ok"}, HEADERS)

    try:

        asset_id = (event.get("pathParameters") or {}).get("id")

        if not asset_id:
            return _response(400, {"message": "Missing asset id"}, HEADERS)

        # =========================================================================
        # Query history from REQUESTS table (source of truth)
        # =========================================================================

        history = get_asset_history(asset_id)

        # =========================================================================
        # Manager / user restriction
        # =========================================================================

        if not scope["full_access"]:
            history = filter_by_location(history, scope["location"])

        # =========================================================================
        # Optional: sort newest first
        # =========================================================================

        history.sort(
            key=lambda x: x.get("jobCreated", ""),
            reverse=True
        )

        # Optional: only completed jobs if "history = completed work"
        completed_history = [
            j for j in history
            if j.get("status") == "complete"
        ]

        print("History:", json.dumps(completed_history, cls=DecimalEncoder))

        return _response(
            200,
            {
                "assetId": asset_id,
                "pendingRequests": len(history),
                "inProgressRequests": 0,
                "completedRequests": len(completed_history),
                "history": completed_history
            },
            HEADERS,
        )

    except Exception as e:
        print("Asset History Error:", str(e))

        return _response(
            500,
            {"message": "Failed to fetch asset history"},
            HEADERS,
        )
