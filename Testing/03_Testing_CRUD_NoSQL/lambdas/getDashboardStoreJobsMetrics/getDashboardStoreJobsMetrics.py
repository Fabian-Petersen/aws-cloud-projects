import boto3
import json
import traceback
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from boto3.dynamodb.conditions import Key
from collections import defaultdict


# ======================================================================================
# DynamoDB
# ======================================================================================

dynamodb = boto3.resource("dynamodb")
action_table = dynamodb.Table("crud-nosql-app-maintenance-action-table")
# assets_table = dynamodb.Table("crud-nosql-app-assets-table")
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


def get_user_access_scope(groups, claims, location=None):
    normalized_groups = set(groups)
    has_full_access = bool(FULL_ACCESS_GROUPS.intersection(normalized_groups))

    # Admin / Technician Full Access
    if has_full_access:
        return {"full_access": True, "location": None}

    return {
        "full_access": False,
        "location": location.lower() if location else None,
    }

    # =========================================================================
    # Manager / Standard User
    # =========================================================================


def get_user_by_sub(user_sub):

    if not user_sub:
        return None

    response = users_table.get_item(
        Key={
            "id": user_sub
        }
    )

    return response.get("Item")

    # if not user:
    #     return {
    #         "full_access": False,
    #         "location": None,
    #     }
    # return {
    #     "full_access": False,
    #     "location": location.lower() if location else None,
    # }


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


# ======================================================================================
# DynamoDB Queries
# ======================================================================================
def get_stores_cost_by_year(store_names=None, filter_year=None, filter_location=None):

    if store_names is None:
        store_names = ["maitland", "bellville", "wynberg", "phillipi"]

    # If drilling down into a specific store/year — return monthly breakdown
    if filter_location and filter_year:
        return get_store_cost_by_month(filter_location, filter_year)

    grouped = defaultdict(lambda: defaultdict(float))

    for store in store_names:
        try:
            resp = action_table.query(
                IndexName="LocationIndex",
                KeyConditionExpression=Key("location").eq(store.lower()),
                ProjectionExpression=(
                    "actionCreated, "
                    "total_cost_parts, "
                    "total_cost_sundries, "
                    "total_cost_contractor"
                )
            )
            items = resp.get("Items", [])

            for job in items:
                date_str = job.get("actionCreated")
                if not date_str:
                    continue
                try:
                    dt = datetime.fromisoformat(date_str)
                    year = str(dt.year)
                    total_cost = (
                        safe_float(job.get("total_cost_parts")) +
                        safe_float(job.get("total_cost_sundries")) +
                        safe_float(job.get("total_cost_contractor"))
                    )
                    grouped[year][store] += total_cost
                except Exception:
                    continue

        except Exception as e:
            print(f"Skipping store '{store}': {str(e)}")
            continue

    result = {}
    for year, stores in grouped.items():
        result[year] = [
            {
                "name": store,
                "value": round(stores.get(store, 0), 2)
            }
            for store in store_names
        ]

    return result


# def get_stores_cost_by_year():
#     store_names = ["maitland", "bellville", "wynberg", "phillipi", "khyalitsha", "golden acre", "middestad"]
#     grouped = defaultdict(lambda: defaultdict(float))

#     for store in store_names:
#         try:
#             resp = action_table.query(
#                 IndexName="LocationIndex",
#                 KeyConditionExpression=Key("location").eq(store.lower()),
#                 ProjectionExpression=(
#                     "actionCreated, "
#                     "total_cost_parts, "
#                     "total_cost_sundries, "
#                     "total_cost_contractor"
#                 )
#             )
#             items = resp.get("Items", [])

#             for job in items:
#                 date_str = job.get("actionCreated")
#                 if not date_str:
#                     continue
#                 try:
#                     dt = datetime.fromisoformat(date_str)
#                     year = str(dt.year)
#                     total_cost = (
#                         safe_float(job.get("total_cost_parts")) +
#                         safe_float(job.get("total_cost_sundries")) +
#                         safe_float(job.get("total_cost_contractor"))
#                     )
#                     grouped[year][store] += total_cost
#                 except Exception:
#                     continue

#         except Exception as e:
#             print(f"Skipping store '{store}': {str(e)}")
#             continue  # store has no data or query failed — skip it

#     # Always include all stores in output, even if they have 0 cost
#     result = {}
#     for year, stores in grouped.items():
#         result[year] = [
#             {
#                 "name": store,
#                 "value": round(stores.get(store, 0), 2)  # defaults to 0 if no data
#             }
#             for store in store_names
#         ]

#     return result

# ======================================================================================
# GET: Store cost by year
# ======================================================================================


def get_store_cost_by_year(store: str) -> dict:

    grouped = defaultdict(lambda: defaultdict(float))

    resp = action_table.query(
        IndexName="LocationIndex",
        KeyConditionExpression=Key("location").eq(store),
        ProjectionExpression=(
            "actionCreated,"
            "total_cost_parts,"
            "total_cost_sundries,"
            "total_cost_contractor"
        )
    )

    items = resp.get("Items", [])

    for job in items:
        date_str = job.get("actionCreated")

        if not date_str:
            continue

        try:
            dt = datetime.fromisoformat(date_str)
            year = str(dt.year)

            total_cost = (
                safe_float(job.get("total_cost_parts")) +
                safe_float(job.get("total_cost_sundries")) +
                safe_float(job.get("total_cost_contractor"))
            )

            grouped[year][store] += total_cost

        except Exception:
            continue

    result = {}

    for year, stores in grouped.items():
        result[year] = [
            {
                "name": store,
                "value": round(stores.get(store, 0), 2)
            }
        ]

    return result

# ======================================================================================
# GET: Store total cost by month per year
# ======================================================================================


def get_store_cost_by_month(location: str, year: str) -> dict:
    monthly = defaultdict(float)

    try:
        resp = action_table.query(
            IndexName="LocationIndex",
            KeyConditionExpression=Key("location").eq(location.lower()),
            ProjectionExpression=(
                "actionCreated, "
                "total_cost_parts, "
                "total_cost_sundries, "
                "total_cost_contractor"
            )
        )
        items = resp.get("Items", [])

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
        "data": [
            {
                "name": MONTH_NAMES[m - 1],
                "value": round(monthly.get(m, 0), 2)
            }
            for m in range(1, 13)
        ]
    }

# ======================================================================================
# GET: Store total cost per month
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


def get_store_jobs_by_month(store: str, month: str, year: str) -> dict:
    jobs = []
    month_int = parse_month(month)

    try:
        resp = action_table.query(
            IndexName="LocationIndex",
            KeyConditionExpression=Key("location").eq(store.lower()),
            ProjectionExpression=(
                # "id, " # add this to the GSI if required
                "actionCreated, "
                "total_cost_parts, "
                "total_cost_sundries, "
                "total_cost_contractor "
                # "description, "
                # "asset, "
                # "status"
            )
        )
        items = resp.get("Items", [])
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
                    # "id": job.get("id"),
                    "date": date_str,
                    # "description": job.get("description"),
                    # "asset": job.get("asset"),
                    # "status": job.get("status"),
                    "costs": {
                        "parts": safe_float(job.get("total_cost_parts")),
                        "sundries": safe_float(job.get("total_cost_sundries")),
                        "contractor": safe_float(job.get("total_cost_contractor")),
                        "total": round(total_cost, 2)
                    }
                })
            except Exception:
                continue
    except Exception as e:
        print(f"Error fetching jobs for '{store}' {month}/{year}: {str(e)}")
    # Sort jobs by date ascending
    jobs.sort(key=lambda j: j["date"])
    return {
        "location": store,
        "month": MONTH_NAMES[int(month_int) - 1],
        "year": year,
        "total_jobs": len(jobs),
        "total_cost": round(sum(j["costs"]["total"] for j in jobs), 2),
        "jobs": jobs
    }


# ======================================================================================
# Scoped Job Fetching
# ======================================================================================

def get_jobs_for_scope(access_scope):

    # Admin / Technician
    if access_scope["full_access"]:

        stores_cost_by_year = get_stores_cost_by_year()
        # print('stores_cost_by_year:', stores_cost_by_year)

        return stores_cost_by_year
    # Manager / User
    location = access_scope["location"]
    # print('location:', location)

    if not location:
        return []

    store_cost_by_year = get_store_cost_by_year(location)
    # print('store_cost_by_year:', store_cost_by_year)
    return store_cost_by_year


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

    print('event:', event)

    # =========================================================================
    # User Claims
    # =========================================================================

    claims = (
        event.get("requestContext", {},)
        .get("authorizer", {},)
        .get("claims", {},)
    )

    # print('claims:', claims)

    user_sub = claims.get("sub")
    user = get_user_by_sub(user_sub)
    location = user.get("location") if user else None

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

    access_scope = get_user_access_scope(groups, claims, location)

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
        # Drilldown: location + year + month → individual jobs
        if filter_location and filter_year and filter_month:
            data = get_store_jobs_by_month(
                filter_location, filter_month, filter_year)

        # Drilldown: location + year → monthly cost breakdown
        elif filter_location and filter_year:
            data = get_store_cost_by_month(filter_location, filter_year)

        # Overview: all stores by year
        else:
            if access_scope["full_access"]:
                data = get_stores_cost_by_year()
            else:
                scoped_location = access_scope["location"]
                if not scoped_location:
                    return _response(403, {"message": "No location assigned"}, HEADERS)
                data = get_stores_cost_by_year(store_names=[scoped_location])

        return _response(200, data, HEADERS)

    except Exception as error:
        import traceback
        traceback.print_exc()
        return _response(500, {"message": "Failed to fetch dashboard metrics"}, HEADERS)
