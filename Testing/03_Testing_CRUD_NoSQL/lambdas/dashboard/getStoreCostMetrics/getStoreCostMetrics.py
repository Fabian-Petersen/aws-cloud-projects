import boto3
import json
import traceback
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from boto3.dynamodb.conditions import Attr, Key
from collections import defaultdict


# ======================================================================================
# DynamoDB
# ======================================================================================

dynamodb = boto3.resource("dynamodb")
action_table = dynamodb.Table("crud-nosql-app-maintenance-action-table")
locations_table = dynamodb.Table("crud-nosql-app-locations-table")
users_table = dynamodb.Table("crud-nosql-app-users-table")

# STORE_NAMES = [
#     "maitland",
#     "bellville",
#     "wynberg",
#     "phillipi",
#     "khyalistha",
#     "golden acre",
#     "somerset west",
#     "middestad mall",
#     "atlantic meat store",
# ]

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
    user_sub = claims.get("sub")

    if "admin" in normalized_groups:
        return {
            "role": "admin",
            "user_sub": user_sub,
            "location": None,
        }

    if "maintenance" in normalized_groups:
        return {
            "role": "maintenance",
            "user_sub": user_sub,
            "location": None,
        }

    # =========================================================================
    # Manager / Standard User
    # =========================================================================

    user = get_user_by_sub(user_sub)
    location = user.get("location") if user else None

    return {
        "role": "location",
        "user_sub": user_sub,
        "location": location.lower() if location else None,
    }


def get_user_by_sub(user_sub):

    if not user_sub:
        return None

    response = users_table.get_item(
        Key={
            "id": user_sub
        }
    )

    return response.get("Item")

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


def safe_parse_date(date_string):
    if not date_string:
        return None

    try:
        parsed_date = datetime.fromisoformat(
            date_string.replace(
                "Z", "+00:00")
        )

        # If datetime is naive, force UTC
        if parsed_date.tzinfo is None:
            parsed_date = parsed_date.replace(
                tzinfo=timezone.utc
            )
        return parsed_date

    except Exception:
        return None


def query_all(table, **kwargs):
    items = []
    response = table.query(**kwargs)
    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = table.query(
            ExclusiveStartKey=response["LastEvaluatedKey"],
            **kwargs,
        )
        items.extend(response.get("Items", []))

    return items


def scan_all(table, **kwargs):
    items = []
    response = table.scan(**kwargs)
    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = table.scan(
            ExclusiveStartKey=response["LastEvaluatedKey"],
            **kwargs,
        )
        items.extend(response.get("Items", []))

    return items


def get_actions_completed_by_user(user_sub):
    if not user_sub:
        return []

    return scan_all(
        action_table,
        FilterExpression=Attr("action_sub").eq(user_sub),
    )


# ======================================================================================
# GET: Store Locations
# ======================================================================================


def get_locations():
    locations = []

    try:
        response = locations_table.scan(
            ProjectionExpression="#loc, #code",
            ExpressionAttributeNames={
                "#loc": "location",
                "#code": "code"
            }
        )

        locations.extend(response.get("Items", []))

        while "LastEvaluatedKey" in response:
            response = locations_table.scan(
                ProjectionExpression="#loc, #code",
                ExpressionAttributeNames={
                    "#loc": "location",
                    "#code": "code"
                },
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )

            locations.extend(response.get("Items", []))

    except Exception as e:
        print(f"Error fetching locations: {str(e)}")

    return locations

# ======================================================================================
# GET: Store cost by year
# ======================================================================================


def get_stores_cost_by_year(
    filter_year=None,
    filter_location=None,
    actions=None,
):

    if filter_location and filter_year:
        return get_store_cost_by_month(
            filter_location,
            filter_year,
            actions=actions,
        )

    locations = get_locations()

    grouped = defaultdict(lambda: defaultdict(float))

    def add_action(job):
        store = str(job.get("location") or "").lower()
        date = safe_parse_date(job.get("actionCreated"))

        if not store or not date:
            return

        total_cost = (
            safe_float(job.get("total_cost_parts"))
            + safe_float(job.get("total_cost_sundries"))
            + safe_float(job.get("total_cost_contractor"))
        )
        grouped[str(date.year)][store] += total_cost

    if actions is not None:
        for job in actions:
            add_action(job)
    else:
        for item in locations:

            store = item.get("location")

            if not store:
                continue

            try:
                items = query_all(
                    action_table,
                    IndexName="LocationIndex",
                    KeyConditionExpression=Key("location").eq(
                        store.lower()
                    ),
                    ProjectionExpression=(
                        "actionCreated, "
                        "total_cost_parts, "
                        "total_cost_sundries, "
                        "total_cost_contractor"
                    )
                )

                for job in items:
                    # LocationIndex already establishes the location. Include it
                    # explicitly so scoped and unscoped actions share aggregation.
                    job.setdefault("location", store)
                    add_action(job)

            except Exception as e:
                print(
                    f"Skipping store '{store}': {str(e)}"
                )

    result = {}

    for year, stores in grouped.items():

        result[year] = [
            {
                "name": item.get("location"),
                "code": item.get("code"),
                "value": round(
                    stores.get(
                        str(item.get("location") or "").lower(),
                        0,
                    ),
                    2
                )
            }
            for item in locations
        ]

    return result

# ======================================================================================
# GET: Store total cost by month for the selected year
# ======================================================================================


def get_store_cost_by_month(
    location: str,
    year: str,
    actions=None,
) -> dict:
    monthly = defaultdict(float)

    try:
        if actions is None:
            items = query_all(
                action_table,
                IndexName="LocationIndex",
                KeyConditionExpression=Key("location").eq(location.lower()),
                ProjectionExpression=(
                    "actionCreated, "
                    "total_cost_parts, "
                    "total_cost_sundries, "
                    "total_cost_contractor"
                )
            )
        else:
            items = [
                action
                for action in actions
                if str(action.get("location") or "").lower()
                == location.lower()
            ]

        for job in items:
            date_str = job.get("actionCreated")
            if not date_str:
                continue
            try:
                dt = datetime.fromisoformat(date_str)
                if str(dt.year) != str(year):
                    continue                        # filter to requested year only
                month = dt.month
                total_cost = (
                    safe_float(job.get("total_cost_parts")) +
                    safe_float(job.get("total_cost_sundries")) +
                    safe_float(job.get("total_cost_contractor"))
                )
                monthly[month] += total_cost
            except Exception:
                continue

    except Exception as e:
        print(f"Error fetching monthly data for '{location}': {str(e)}")

    # Always return all 12 months even if no data
    return {
        "location": location,
        "year": year,
        "data": {
            year: [
                {
                    "name": MONTH_NAMES[m - 1],
                    "value": round(monthly.get(m, 0), 2)
                }
                for m in range(1, 13)
            ]}
    }

# ======================================================================================
# GET: Total cost of jobs of selected store for the month
# ======================================================================================


MONTH_NAMES = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]

# Map month name → number to handle either format from frontend
MONTH_NAME_TO_NUM = {name.lower(): i + 1 for i, name in enumerate(MONTH_NAMES)}


def parse_month(month: str) -> int:
    """Accept either a number '3' or a name 'may'/'Mar' and return int 1-12."""
    try:
        return int(month)
    except ValueError:
        num = MONTH_NAME_TO_NUM.get(month.strip().lower())
        if num is None:
            raise ValueError(f"Unrecognised month: '{month}'")
        return num


def format_jobs_by_month(items, store: str, month: str, year: str) -> dict:
    jobs = []
    month_int = parse_month(month)

    for job in items:
        date_str = job.get("actionCreated")
        if not date_str:
            continue
        try:
            dt = datetime.fromisoformat(date_str)
            if str(dt.year) != str(year):
                continue
            if str(dt.month) != str(month_int):
                continue
            total_cost = (
                safe_float(job.get("total_cost_parts")) +
                safe_float(job.get("total_cost_sundries")) +
                safe_float(job.get("total_cost_contractor"))
            )
            jobs.append({
                "request_id": job.get("request_id"),
                "action_id": job.get("id"),
                "assetID": job.get("assetID"),
                "date": date_str,
                "costs": {
                    "parts": safe_float(job.get("total_cost_parts")),
                    "sundries": safe_float(job.get("total_cost_sundries")),
                    "contractor": safe_float(job.get("total_cost_contractor")),
                    "total": round(total_cost, 2)
                }
            })
        except Exception:
            continue

    jobs.sort(key=lambda j: j["date"])
    return {
        "location": store,
        "year": year,
        "month": MONTH_NAMES[int(month_int) - 1],
        "total_jobs": len(jobs),
        "total_cost": round(sum(j["costs"]["total"] for j in jobs), 2),
        "jobs": jobs
    }


def get_store_jobs_by_month(
    store: str,
    month: str,
    year: str,
    actions=None,
) -> dict:
    try:
        if actions is None:
            items = query_all(
                action_table,
                IndexName="LocationIndex",
                KeyConditionExpression=Key("location").eq(store.lower()),
                ProjectionExpression=(
                    "request_id, "
                    "id, "
                    "assetID, "
                    "actionCreated, "
                    "total_cost_parts, "
                    "total_cost_sundries, "
                    "total_cost_contractor "
                )
            )
        else:
            items = [
                action
                for action in actions
                if str(action.get("location") or "").lower()
                == store.lower()
            ]
    except Exception as e:
        print(f"Error fetching jobs for '{store}' {month}/{year}: {str(e)}")
        items = []

    return format_jobs_by_month(items, store, month, year)


# ======================================================================================
# Safe Float for the cost data
# ======================================================================================


def safe_float(value):
    try:
        if value is None:
            return 0.0

        value_str = str(value).strip().lower()

        if value_str in ("", "empty", "none", "null", "nan"):
            return 0.0

        return float(value_str)

    except (ValueError, TypeError):
        return 0.0


# ======================================================================================
# Lambda Handler
# ======================================================================================


def lambda_handler(event, context):

    print('event:', json.dumps(event))

    # =========================================================================
    # User Claims
    # =========================================================================

    claims = (
        event.get("requestContext", {},)
        .get("authorizer", {},)
        .get("claims", {},)
    )

    groups = parse_groups(claims.get("cognito:groups"))

    # --- Parse query params ---
    query_params = event.get("queryStringParameters") or {}
    filter_location = query_params.get("location")
    filter_year = query_params.get("year")
    filter_month = query_params.get("month")

    # print('groups:', groups)

    # =========================================================================
    # Access Scope
    # =========================================================================

    access_scope = get_user_access_scope(groups, claims)

    # print('access scope:', access_scope)

    # =========================================================================
    # CORS
    # =========================================================================

    headers = (event.get("headers") or {})

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
        # ---------------------------------------------------------------------
        # Level 3: Store + Year + Month → individual jobs
        # ---------------------------------------------------------------------
        role = access_scope["role"]
        scoped_location = access_scope["location"]
        user_sub = access_scope["user_sub"]

        if role == "maintenance" and not user_sub:
            return _response(
                403,
                {"message": "User sub not found in token"},
                HEADERS,
            )

        if role == "location" and not scoped_location:
            return _response(
                403,
                {"message": "No location assigned"},
                HEADERS,
            )

        scoped_actions = None

        if role == "maintenance":
            scoped_actions = get_actions_completed_by_user(user_sub)

        if filter_location and filter_year and filter_month:
            authorized_location = (
                filter_location.lower()
                if role in {"admin", "maintenance"}
                else scoped_location
            )
            data = get_store_jobs_by_month(
                authorized_location,
                filter_month,
                filter_year,
                actions=scoped_actions,
            )

        # ---------------------------------------------------------------------
        # Level 2: Store + Year → monthly cost breakdown
        # ---------------------------------------------------------------------
        elif filter_location and filter_year:
            authorized_location = (
                filter_location.lower()
                if role in {"admin", "maintenance"}
                else scoped_location
            )
            data = get_store_cost_by_month(
                authorized_location,
                filter_year,
                actions=scoped_actions,
            )

        # ---------------------------------------------------------------------
        # Level 1: Initial dashboard data
        #
        # Admin:
        #   Return total cost per site
        #
        # Manager/User:
        #   Return monthly cost for their assigned site
        #
        # IMPORTANT:
        # Return ONLY the dictionary.
        # The aggregator adds:
        #
        #   "storeCost": <this response>
        # ---------------------------------------------------------------------
        else:
            if role in {"admin", "maintenance"}:
                data = get_stores_cost_by_year(
                    actions=scoped_actions,
                )

            else:
                year = filter_year or str(datetime.now().year)

                monthly_data = get_store_cost_by_month(
                    scoped_location,
                    year,
                )

                data = monthly_data["data"]

        print('data:', json.dumps(data))

        return _response(200, data, HEADERS)

    except Exception:
        traceback.print_exc()

        return _response(
            500,
            {"message": "Failed to fetch dashboard metrics"},
            HEADERS,
        )
