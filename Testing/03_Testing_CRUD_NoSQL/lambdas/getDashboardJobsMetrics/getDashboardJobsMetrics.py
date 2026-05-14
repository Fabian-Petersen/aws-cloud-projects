import json
from decimal import Decimal
from datetime import datetime, timezone, timedelta

import boto3
from boto3.dynamodb.conditions import Key


# ======================================================================================
# DynamoDB
# ======================================================================================

dynamodb = boto3.resource("dynamodb")

jobs_table = dynamodb.Table(
    "crud-nosql-app-maintenance-request-table"
)


# ======================================================================================
# JSON Encoder
# ======================================================================================

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):

        if isinstance(obj, Decimal):
            return float(obj)

        return super().default(obj)


# ======================================================================================
# Access Control
# ======================================================================================

FULL_ACCESS_GROUPS = {
    "admin",
    "technician",
}


def parse_groups(groups_claim):

    if not groups_claim:
        return []

    if isinstance(groups_claim, list):
        return [
            str(group).lower()
            for group in groups_claim
        ]

    if isinstance(groups_claim, str):

        try:
            parsed = json.loads(groups_claim)

            if isinstance(parsed, list):
                return [
                    str(group).lower()
                    for group in parsed
                ]

        except Exception:
            pass

        return [
            group.strip().lower()
            for group in groups_claim.split(",")
        ]

    return []


def get_user_access_scope(groups, claims):

    normalized_groups = set(groups)

    has_full_access = bool(
        FULL_ACCESS_GROUPS.intersection(
            normalized_groups
        )
    )

    if has_full_access:

        return {
            "full_access": True,
            "location": None,
        }

    return {
        "full_access": False,
        "location": claims.get(
            "custom:location"
        ),
    }


# ======================================================================================
# Helpers
# ======================================================================================

def _response(status_code, body, headers):

    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(
            body,
            cls=DecimalEncoder,
        ),
    }


def calculate_percentage_change(
    previous,
    current,
):

    if previous == 0:

        if current == 0:
            return 0

        return 100

    return round(
        ((current - previous) / previous) * 100
    )


def safe_parse_date(date_string):

    if not date_string:
        return None

    try:
        return datetime.fromisoformat(
            date_string.replace(
                "Z",
                "+00:00",
            )
        )

    except Exception:
        return None


def get_month_ranges():

    today = datetime.now(
        timezone.utc
    )

    current_month_start = today.replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    current_month_end = today

    previous_month_end = (
        current_month_start
        - timedelta(seconds=1)
    )

    previous_month_start = (
        previous_month_end.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
    )

    return {
        "current_month_start":
            current_month_start,

        "current_month_end":
            current_month_end,

        "previous_month_start":
            previous_month_start,

        "previous_month_end":
            previous_month_end,
    }


# ======================================================================================
# DynamoDB Queries
# ======================================================================================

def query_jobs_by_status(status):

    items = []

    response = jobs_table.query(
        IndexName="StatusIndex",
        KeyConditionExpression=Key("status").eq(status),
    )

    items.extend(
        response.get("Items", [])
    )

    while "LastEvaluatedKey" in response:

        response = jobs_table.query(
            IndexName="StatusIndex",
            KeyConditionExpression=Key("status").eq(status),
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )

        items.extend(
            response.get("Items", [])
        )

    return items


def query_jobs_by_location(location):

    items = []

    response = jobs_table.query(
        IndexName="LocationIndex",
        KeyConditionExpression=Key("location").eq(location),
    )

    items.extend(
        response.get("Items", [])
    )

    while "LastEvaluatedKey" in response:

        response = jobs_table.query(
            IndexName="LocationIndex",
            KeyConditionExpression=Key("location").eq(location),
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )

        items.extend(
            response.get("Items", [])
        )

    return items


# ======================================================================================
# Scoped Job Fetching
# ======================================================================================

def get_jobs_for_scope(access_scope):

    # Admin / Technician
    if access_scope["full_access"]:

        pending_jobs = query_jobs_by_status(
            "pending"
        )

        approved_jobs = query_jobs_by_status(
            "in progress"
        )

        completed_jobs = query_jobs_by_status(
            "completed"
        )

        return (
            pending_jobs
            + approved_jobs
            + completed_jobs
        )

    # Manager / User
    location = access_scope["location"]

    if not location:
        return []

    return query_jobs_by_location(
        location
    )


# ======================================================================================
# Metric Helpers
# ======================================================================================

def split_jobs_by_month(jobs):

    ranges = get_month_ranges()

    current_jobs = []

    previous_jobs = []

    for job in jobs:

        created_at = safe_parse_date(
            job.get("jobCreated")
        )

        if not created_at:
            continue

        if (
            created_at
            >= ranges["current_month_start"]
        ):

            current_jobs.append(job)

        elif (
            ranges["previous_month_start"]
            <= created_at
            <= ranges["previous_month_end"]
        ):

            previous_jobs.append(job)

    return (
        current_jobs,
        previous_jobs,
    )


# ======================================================================================
# Pending Metrics
# ======================================================================================

def get_pending_metrics(jobs):

    pending_jobs = [
        job for job in jobs
        if job.get("status") == "pending"
    ]

    current_jobs, previous_jobs = (
        split_jobs_by_month(
            pending_jobs
        )
    )

    return {
        "pendingRequests": {
            "value": len(
                pending_jobs
            ),
            "valueChange":
                calculate_percentage_change(
                    len(previous_jobs),
                    len(current_jobs),
            ),
        }
    }


# ======================================================================================
# Approved Metrics
# ======================================================================================

def get_approved_metrics(jobs):

    approved_jobs = [
        job for job in jobs
        if job.get("status")
        == "in progress"
    ]

    current_jobs, previous_jobs = (
        split_jobs_by_month(
            approved_jobs
        )
    )

    return {
        "approvedRequests": {
            "value": len(
                approved_jobs
            ),
            "valueChange":
                calculate_percentage_change(
                    len(previous_jobs),
                    len(current_jobs),
            ),
        }
    }


# ======================================================================================
# Overdue Metrics
# ======================================================================================

def get_overdue_metrics(jobs):

    today = datetime.now(
        timezone.utc
    )

    overdue_jobs = []

    for job in jobs:

        if (
            job.get("status")
            != "in progress"
        ):
            continue

        due_date = safe_parse_date(
            job.get("targetDate")
        )

        if not due_date:
            continue

        if due_date < today:
            overdue_jobs.append(job)

    current_jobs, previous_jobs = (
        split_jobs_by_month(
            overdue_jobs
        )
    )

    return {
        "overdueRequests": {
            "value": len(
                overdue_jobs
            ),
            "valueChange":
                calculate_percentage_change(
                    len(previous_jobs),
                    len(current_jobs),
            ),
        }
    }


# ======================================================================================
# Completed Metrics
# ======================================================================================

def get_completed_metrics(jobs):

    completed_jobs = [
        job for job in jobs
        if job.get("status")
        == "completed"
    ]

    current_jobs, previous_jobs = (
        split_jobs_by_month(
            completed_jobs
        )
    )

    return {
        "totalCompleted": {
            "value": len(
                completed_jobs
            ),
            "valueChange":
                calculate_percentage_change(
                    len(previous_jobs),
                    len(current_jobs),
            ),
        }
    }


# ======================================================================================
# Lambda Handler
# ======================================================================================

def handler(event, context):

    # =========================================================================
    # User Claims
    # =========================================================================

    claims = (
        event.get("requestContext", {},)
        .get("authorizer", {},)
        .get("claims", {},)
    )

    groups = parse_groups(
        claims.get("cognito:groups")
    )

    # =========================================================================
    # Access Scope
    # =========================================================================

    access_scope = (
        get_user_access_scope(groups, claims,)
    )

    # =========================================================================
    # CORS
    # =========================================================================

    headers = (
        event.get("headers")
        or {}
    )

    origin = (
        headers.get("origin")
        or headers.get("Origin")
        or ""
    )

    allowed_origins = [
        "https://www.crud-nosql.app.fabian-portfolio.net",
        "https://crud-nosql.app.fabian-portfolio.net",
        "http://localhost:5173",
    ]

    allowed_origin = (
        origin
        if origin in allowed_origins
        else ""
    )

    HEADERS = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": allowed_origin,
        "Access-Control-Allow-Methods": "GET,OPTIONS",
        "Access-Control-Allow-Headers":
            "Content-Type,Authorization,"
            "X-Amz-Date,X-Api-Key,"
            "X-Amz-Security-Token,"
            "X-Requested-With",
        "Access-Control-Allow-Credentials": "true",
    }

    # =========================================================================
    # OPTIONS
    # =========================================================================

    method = (
        event.get("httpMethod")
        or event.get("requestContext", {},)
        .get("http", {},)
        .get("method")
    )

    if method == "OPTIONS":

        return _response(200, {"message": "Success"}, HEADERS,)

    # =========================================================================
    # Main Logic
    # =========================================================================

    try:

        jobs = get_jobs_for_scope(access_scope)

        dashboard_metrics = {
            **get_pending_metrics(jobs),
            **get_approved_metrics(jobs),
            **get_overdue_metrics(jobs),
            **get_completed_metrics(jobs),
        }

        return _response(200, dashboard_metrics, HEADERS,)

    except Exception as error:

        print("Dashboard Metrics Error:", str(error),)

        return _response(500, {"message": "Failed to fetch dashboard metrics"}, HEADERS,)
