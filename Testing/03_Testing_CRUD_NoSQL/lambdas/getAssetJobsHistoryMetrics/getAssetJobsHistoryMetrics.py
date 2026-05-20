import boto3
import json
from decimal import Decimal
from boto3.dynamodb.conditions import Key
from datetime import datetime, timedelta, timezone
from collections import defaultdict

# ======================================================================================
# DynamoDB
# ======================================================================================

dynamodb = boto3.resource("dynamodb")

jobs_table = dynamodb.Table("crud-nosql-app-maintenance-request-table")
users_table = dynamodb.Table("crud-nosql-app-users-table")
assets_table = dynamodb.Table("crud-nosql-app-assets-table")
action_table = dynamodb.Table("crud-nosql-app-maintenance-action-table")

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

# ======================================================================================
# Return Human Readible date
# ======================================================================================


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
# GET ASSET BARCODE ID
# ======================================================================================

def get_asset_barcode_id(asset_id) -> str:

    response = assets_table.query(
        KeyConditionExpression=Key("id").eq(asset_id)
    )

    barcode_id = response['Items'][0]['assetID']

    return barcode_id

# ======================================================================================
# GET ASSET ACTION DATA
# ======================================================================================


def get_asset_action_history(asset_id) -> dict:

    items = []

    response = action_table.query(
        KeyConditionExpression=Key("assetID").eq(asset_id),
        IndexName="AssetIdIndex"
    )

    while "LastEvaluatedKey" in response:
        response = action_table.query(
            IndexName="AssetIdIndex",
            KeyConditionExpression=boto3.Key("assetID").eq(asset_id),
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
    items.extend(response.get("Items", []))

    return items


# ======================================================================================
# JOB REQUEST HISTORY QUERY
# ======================================================================================

def get_asset_request_history(asset_id) -> dict:

    items = []

    response = jobs_table.query(
        IndexName="AssetIdIndex",
        KeyConditionExpression=Key("assetID").eq(asset_id)
    )

    # print("response:", response)
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
# GET LAST COMPLETED JOB ======================================================================================


def get_last_completed_action(asset_id):
    """
    Retrieves the most recent action for an asset and returns its completed_at timestamp.

    Uses AssetIdIndex (assetID + actionCreated) sorted descending to get the latest action.

    Args:
        asset_id (str): Asset identifier.

    Returns:
        str | None: The completed_at timestamp of the latest action, or None if not found.
    """

    response = action_table.query(
        IndexName="AssetIdIndex",
        KeyConditionExpression=Key("assetID").eq(asset_id),
        ScanIndexForward=False,  # newest first
        Limit=1
    )

    items = response.get("Items", [])

    if not items:
        return None

    latest_action = items[0]

    return to_human_date(latest_action.get("completed_at"))

# =========================================================================
# Get the total cost of repairs
# =========================================================================


def safe_float(value):
    """
    Converts DynamoDB numeric/string values safely to float.
    """
    if value is None:
        return 0.0

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        value = value.strip()
        if value == "":
            return 0.0
        return float(value)

    return 0.0


def calculate_asset_cost(asset_id) -> float:
    """
    Calculates total cost for an asset across all jobs.
    Cost breakdown per job:
        - total_cost_parts
        - total_cost_sundries
        - total_cost_contractor
    Returns:
            "total_cost": float,
    """
    response = action_table.query(
        IndexName="AssetIdIndex",
        KeyConditionExpression=Key("assetID").eq(asset_id),
        ProjectionExpression="total_cost_parts, total_cost_sundries, total_cost_contractor"
    )

    items = response.get("Items", [])

    total_cost = 0.0

    for job in items:
        parts = safe_float(job.get("total_cost_parts"))
        sundries = safe_float(job.get("total_cost_sundries"))
        contractor = safe_float(job.get("total_cost_contractor"))

        total_cost += (parts + sundries + contractor)

    return round(total_cost, 2)

# =========================================================================
# Get the total cost of repairs for an asset by month
# =========================================================================


def safe_float(value):
    if value is None:
        return 0.0
    return float(str(value))


def get_asset_cost_by_year(asset_id):
    """
    Returns cost grouped by year and month for charting.
    Format:
    {
        "2026": [{name: "Jan", value: 123}],
        "2025": [{name: "Jan", value: 456}]
    }
    """

    response = action_table.query(
        IndexName="AssetIdIndex",
        KeyConditionExpression=Key("assetID").eq(asset_id),
        ProjectionExpression=(
            "actionCreated, "
            "total_cost_parts, "
            "total_cost_sundries, "
            "total_cost_contractor"
        )
    )

    items = response.get("Items", [])

    grouped = defaultdict(lambda: defaultdict(float))

    for job in items:
        date_str = job.get("actionCreated")
        if not date_str:
            continue

        try:
            dt = datetime.fromisoformat(date_str)

            year = str(dt.year)
            month = dt.strftime("%b")  # Jan, Feb, etc.

            total_cost = (
                safe_float(job.get("total_cost_parts")) +
                safe_float(job.get("total_cost_sundries")) +
                safe_float(job.get("total_cost_contractor"))
            )

            grouped[year][month] += total_cost

        except Exception:
            continue

    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    result = {}

    for year, months in grouped.items():
        result[year] = [
            {
                "name": m,
                "value": round(months.get(m, 0), 2)
            }
            for m in month_order
        ]

    return result

# =========================================================================
# Get MTTR
# =========================================================================


def parse_time(ts):
    """
    Adjust this depending on your timestamp format.
    Assumes ISO 8601 strings.
    """
    return datetime.fromisoformat(ts)


def get_mttr(asset_id):
    """
    Calculates Mean Time To Repair (MTTR) for an asset using action records.

    MTTR = average(completed_at - actionCreated) for all completed actions.

    Returns:
        float | None: MTTR in hours (or None if insufficient data)
    """

    response = action_table.query(
        IndexName="AssetIdIndex",
        KeyConditionExpression=Key("assetID").eq(asset_id),
        ScanIndexForward=False
    )

    items = response.get("Items", [])

    repair_times = []

    for item in items:
        action_start = item.get("actionCreated")
        completed_at = item.get("completed_at")

        # Only include completed actions
        if not action_start or not completed_at:
            continue

        try:
            start = parse_time(action_start)
            end = parse_time(completed_at)

            duration_hours = (end - start).total_seconds() / 3600
            repair_times.append(duration_hours)

        except Exception:
            continue

    if not repair_times:
        return None

    return sum(repair_times) / len(repair_times)


# ======================================================================================
# BUILD CLEAN COMPLETED HISTORY
# Joins completed actions with their parent requests to pull jobCreated + description,
# then projects only the fields needed by the history dashboard.
# ======================================================================================

HISTORY_ACTION_FIELDS = {
    "request_id",
    "location",
    "assetID",
    "jobcardNumber",
    "sundries",
    "total_cost_sundries",
    "parts",
    "total_cost_parts",
    "contractor",
    "total_cost_contractor",
    "actioned_by",
    "completed_at",
}


def build_completed_history(completed_actions: list, request_history: list) -> list:
    """
    Merges completed action records with their parent request to produce
    a clean history list containing only the dashboard fields.

    Fields sourced from the requests table : jobCreated, description
    Fields sourced from the actions table  : jobcardNumber, sundries,
        total_cost_sundries, parts, total_cost_parts, contractor,
        total_cost_contractor, actioned_by, completed_at

    Args:
        completed_actions: Filtered list of action items with status == "complete".
        request_history:   Full list of request items for the same asset.

    Returns:
        List of dicts containing only the specified dashboard fields.
    """
    # Build a lookup map from requestId -> request item for O(1) joins
    request_map: dict = {r["id"]: r for r in request_history if "id" in r}

    history = []

    for action in completed_actions:
        request_id = action.get("request_id")
        request = request_map.get(request_id, {})

        record = {
            # From requests table
            "jobCreated": to_human_date(request["jobCreated"]) if request.get("jobCreated") else None,
            "description": request.get("description"),
            "equipment": request.get("equipment"),
            # From actions table — only the required fields
            **{field: action.get(field) for field in HISTORY_ACTION_FIELDS},
        }

        # Convert completed_at to human-readable if present
        if record.get("completed_at"):
            record["completed_at"] = to_human_date(record["completed_at"])

        history.append(record)

    return history


# ======================================================================================
# Lambda Handler
# ======================================================================================

def lambda_handler(event, context):
    # print("event:", event)

    claims = event.get("requestContext", {}).get(
        "authorizer", {}).get("claims", {})
    # print("claims:", claims)

    groups = parse_groups(claims.get("cognito:groups"))
    # print("groups:", groups)

    print("event:", event)

    scope = get_user_scope(groups, claims)

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

        assetID = get_asset_barcode_id(asset_id)

        # print("assetID:", assetID)

        if not asset_id:
            return _response(400, {"message": "Missing asset id"}, HEADERS)

        # =========================================================================
        # Query history from REQUESTS table (source of truth)
        # =========================================================================
        request_history = get_asset_request_history(assetID)

        # =========================================================================
        # Query jobs actioned from ACTION table (source of truth)
        # =========================================================================
        action_history = get_asset_action_history(assetID)

        # =========================================================================
        # Manager / user restriction
        # =========================================================================

        if not scope["full_access"]:
            request_history = filter_by_location(
                request_history, scope["location"])

        if not scope["full_access"]:
            action_history = filter_by_location(
                action_history, scope["location"])

        # =========================================================================
        # Optional: sort newest first
        # =========================================================================

        request_history.sort(
            key=lambda x: x.get("jobCreated", ""),
            reverse=True
        )

        action_history.sort(
            key=lambda x: x.get("actionCreated", ""),
            reverse=True
        )

        # Optional: only completed jobs if "history = completed work"
        completed_history = [
            j for j in action_history
            if j.get("status") == "complete"
        ]

        inProgress_history = [
            j for j in request_history
            if j.get("status") == "in progress"
        ]

        pending_history = [
            j for j in request_history
            if j.get("status") == "pending"
        ]

        # =========================================================================
        # Get last completed job
        # =========================================================================
        last_completed_job = get_last_completed_action(assetID)

        # =========================================================================
        # Reliability Metrics
        # =========================================================================

        mttr = get_mttr(assetID)
        total_cost = calculate_asset_cost(assetID)
        total_cost_by_year = get_asset_cost_by_year(assetID)
        print("total_cost_by_year:", json.dumps(
            total_cost_by_year, cls=DecimalEncoder))

        return _response(
            200,
            {"last_completed_job": last_completed_job,
                "assetId": asset_id,
                "metrics": {
                    "pendingRequests": {
                        "value": len(pending_history),
                    },
                    "inProgressRequests": {
                        "value": len(inProgress_history),
                    },
                    "completedRequests": {
                        "value": len(completed_history),
                    },
                    "total_cost": {
                        "value": total_cost
                    }
                },
                "reliability": [
                    {
                        "mtbf": 0
                    },
                    {
                        "mttr": mttr,
                    },
                    {
                        "availability": 0
                    },
                    {
                        "failureCount": len(completed_history)
                    }
                ],
                "history": build_completed_history(completed_history, request_history),
                "total_cost_by_month": total_cost_by_year
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
