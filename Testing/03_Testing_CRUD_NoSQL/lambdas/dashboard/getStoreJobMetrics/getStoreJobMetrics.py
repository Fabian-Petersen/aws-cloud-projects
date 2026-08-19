import boto3
import json
import traceback
from decimal import Decimal
from datetime import datetime
from boto3.dynamodb.conditions import Key
from collections import defaultdict


# ======================================================================================
# DynamoDB
# ======================================================================================

dynamodb = boto3.resource("dynamodb")

request_table = dynamodb.Table(
    "crud-nosql-app-maintenance-request-table"
)

users_table = dynamodb.Table(
    "crud-nosql-app-users-table"
)


# ======================================================================================
# Constants
# ======================================================================================

FULL_ACCESS_GROUPS = {
    "admin",
    "technician",
}

DEFAULT_STATUSES = [
    "pending",
    "in progress",
    "completed",
    "cancelled",
]


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
    """
    Normalise Cognito group claims into a list of lowercase group names.

    Supports:
        - list
        - JSON encoded list
        - comma-separated string
    """

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


def get_user_by_sub(user_sub):
    """
    Fetch the authenticated user's record from the users table.
    """

    if not user_sub:
        return None

    response = users_table.get_item(
        Key={
            "id": user_sub
        }
    )

    return response.get("Item")


def get_user_access_scope(groups, location=None):
    """
    Determine whether the authenticated user can access all sites
    or only their assigned site.
    """

    normalized_groups = set(groups)

    has_full_access = bool(
        FULL_ACCESS_GROUPS.intersection(normalized_groups)
    )

    if has_full_access:
        return {
            "full_access": True,
            "location": None,
        }

    return {
        "full_access": False,
        "location": location.lower() if location else None,
    }


# ======================================================================================
# Response Helper
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


# ======================================================================================
# Date Helper
# ======================================================================================

def safe_parse_date(date_string):
    """
    Safely parse an ISO date returned by DynamoDB.

    Returns:
        datetime | None
    """

    if not date_string:
        return None

    try:

        return datetime.fromisoformat(
            str(date_string).replace("Z", "+00:00")
        )

    except Exception:
        return None


# ======================================================================================
# DynamoDB Helpers
# ======================================================================================

def query_jobs_by_status(status):
    """
    Query all maintenance requests for a particular status through
    the StatusIndex.

    DynamoDB Query results are paginated, so LastEvaluatedKey is
    followed until all records have been retrieved.
    """

    items = []

    query_kwargs = {
        "IndexName": "StatusIndex",
        "KeyConditionExpression": Key("status").eq(status),
        "ProjectionExpression": (
            "#status, "
            "#location, "
            "jobCreated"
        ),
        "ExpressionAttributeNames": {
            "#status": "status",
            "#location": "location"
        },
    }

    while True:

        response = request_table.query(
            **query_kwargs
        )

        items.extend(
            response.get("Items", [])
        )

        last_key = response.get(
            "LastEvaluatedKey"
        )

        if not last_key:
            break

        query_kwargs["ExclusiveStartKey"] = last_key

    return items


# ======================================================================================
# GET: Job counts by site/year
# ======================================================================================

def get_jobs_by_status(status, locations=None, filter_year=None):
    """
    Aggregate maintenance requests by location and year.

    Example return:

        {
            "2026": [
                {
                    "name": "maitland",
                    "value": 10
                },
                {
                    "name": "bellville",
                    "value": 6
                }
            ]
        }

    Args:
        status:
            Job status to query.

        locations:
            Optional list of permitted locations.

        filter_year:
            Optional year. If supplied, only that year is returned.
    """

    grouped = defaultdict(
        lambda: defaultdict(int)
    )

    allowed_locations = None

    if locations:
        allowed_locations = {
            location.lower()
            for location in locations
        }

    try:

        items = query_jobs_by_status(
            status
        )

        for job in items:

            location = job.get("location")

            if not location:
                continue

            location = str(location).lower()

            # -----------------------------------------------------------------
            # Access control
            # -----------------------------------------------------------------

            if (
                allowed_locations is not None
                and location not in allowed_locations
            ):
                continue

            # -----------------------------------------------------------------
            # Date
            # -----------------------------------------------------------------

            date = safe_parse_date(
                job.get("jobCreated")
            )

            if not date:
                continue

            year = str(date.year)

            # -----------------------------------------------------------------
            # Optional year filter
            # -----------------------------------------------------------------

            if filter_year and year != str(filter_year):
                continue

            grouped[year][location] += 1

    except Exception as e:

        print(
            f"Error fetching jobs for status "
            f"'{status}': {str(e)}"
        )

    # -------------------------------------------------------------------------
    # Convert to Recharts-compatible structure
    # -------------------------------------------------------------------------

    result = {}

    for year, locations_data in sorted(
        grouped.items()
    ):

        result[year] = [
            {
                "name": location,
                "value": locations_data[location],
            }
            for location in sorted(locations_data)
        ]

    return result


# ======================================================================================
# GET: All job statuses by site
# ======================================================================================

def get_store_job_metrics(
    locations=None,
    filter_year=None,
    statuses=None,
):
    """
    Return maintenance request counts grouped by status, year and site.

    This is the main function used by the dashboard.

    Example:

        {
            "pending": {
                "2026": [
                    {"name": "maitland", "value": 10},
                    {"name": "bellville", "value": 6}
                ]
            },
            "in-progress": {
                "2026": [
                    {"name": "maitland", "value": 4},
                    {"name": "bellville", "value": 2}
                ]
            }
        }

    The result is intentionally returned as a dictionary rather than
    wrapping it in another property. The dashboard aggregator can
    therefore add:

        "storeJobs": <this response>
    """

    statuses = statuses or DEFAULT_STATUSES

    result = {}

    for status in statuses:

        result[status] = get_jobs_by_status(
            status=status,
            locations=locations,
            filter_year=filter_year,
        )

    return result


# ======================================================================================
# GET: Job metrics for a specific site
# ======================================================================================

def get_store_job_metrics_by_site(
    location,
    status,
    year,
):
    """
    Return monthly job counts for a selected site/status/year.

    This is intended for the first Recharts drilldown:

        Site
          ↓
        Year
          ↓
        Months

    Example:

        {
            "location": "maitland",
            "status": "pending",
            "year": "2026",
            "data": {
                "2026": [
                    {"name": "Jan", "value": 2},
                    {"name": "Feb", "value": 4},
                    {"name": "Mar", "value": 1},
                    ...
                ]
            }
        }
    """

    location = location.lower()
    monthly = defaultdict(int)

    try:

        items = query_jobs_by_status(
            status
        )

        for job in items:

            job_location = job.get(
                "location"
            )

            if not job_location:
                continue

            if str(job_location).lower() != location:
                continue

            date = safe_parse_date(
                job.get("jobCreated")
            )

            if not date:
                continue

            if str(date.year) != str(year):
                continue

            monthly[date.month] += 1

    except Exception as e:

        print(
            f"Error fetching site job metrics "
            f"for '{location}': {str(e)}"
        )

    month_names = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]

    return {
        "location": location,
        "status": status,
        "year": year,
        "data": {
            str(year): [
                {
                    "name": month_names[month - 1],
                    "value": monthly.get(
                        month,
                        0,
                    ),
                }
                for month in range(1, 13)
            ]
        },
    }


# ======================================================================================
# Lambda Handler
# ======================================================================================

def lambda_handler(event, context):

    print("event:", json.dumps(event))

    # =========================================================================
    # User Claims
    # =========================================================================

    claims = (
        event
        .get("requestContext", {})
        .get("authorizer", {})
        .get("claims", {})
    )

    user_sub = claims.get("sub")

    user = get_user_by_sub(
        user_sub
    )

    user_location = (
        user.get("location")
        if user
        else None
    )

    groups = parse_groups(
        claims.get("cognito:groups")
    )

    access_scope = get_user_access_scope(
        groups,
        user_location,
    )

    # =========================================================================
    # Query Parameters
    # =========================================================================

    query_params = (
        event.get("queryStringParameters")
        or {}
    )

    filter_location = query_params.get(
        "location"
    )

    filter_status = query_params.get(
        "status"
    )

    filter_year = query_params.get(
        "year"
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
        "Access-Control-Allow-Headers": (
            "Content-Type,Authorization,"
            "X-Amz-Date,X-Api-Key,"
            "X-Amz-Security-Token,"
            "X-Requested-With"
        ),
        "Access-Control-Allow-Credentials": "true",
    }

    # =========================================================================
    # OPTIONS
    # =========================================================================

    method = (
        event.get("httpMethod")
        or event
        .get("requestContext", {})
        .get("http", {})
        .get("method")
    )

    if method == "OPTIONS":

        return _response(
            200,
            {"message": "Success"},
            HEADERS,
        )

    # =========================================================================
    # Main Logic
    # =========================================================================

    try:

        # =====================================================================
        # Level 3:
        #
        # Site + Status + Year
        #
        # Example:
        #
        # ?location=maitland&status=pending&year=2026
        #
        # Returns monthly data for the selected site.
        # =====================================================================

        if (
            filter_location
            and filter_status
            and filter_year
        ):

            # -------------------------------------------------------------
            # Managers / standard users cannot request another location.
            # -------------------------------------------------------------

            if not access_scope["full_access"]:

                scoped_location = (
                    access_scope["location"]
                )

                if not scoped_location:

                    return _response(
                        403,
                        {
                            "message":
                                "No location assigned"
                        },
                        HEADERS,
                    )

                filter_location = (
                    scoped_location
                )

            data = get_store_job_metrics_by_site(
                location=filter_location,
                status=filter_status.lower(),
                year=filter_year,
            )

        # =====================================================================
        # Level 2:
        #
        # Site + Status
        #
        # If year is supplied by frontend, return that year's site metric.
        # Otherwise current year is used.
        # =====================================================================

        elif (
            filter_location
            and filter_status
        ):

            if not access_scope["full_access"]:

                scoped_location = (
                    access_scope["location"]
                )

                if not scoped_location:

                    return _response(
                        403,
                        {
                            "message":
                                "No location assigned"
                        },
                        HEADERS,
                    )

                filter_location = (
                    scoped_location
                )

            year = (
                filter_year
                or str(datetime.now().year)
            )

            data = get_store_job_metrics_by_site(
                location=filter_location,
                status=filter_status.lower(),
                year=year,
            )

        # =====================================================================
        # Level 1:
        #
        # Initial dashboard request.
        #
        # Admin / Technician:
        #     All sites.
        #
        # Manager / User:
        #     Only assigned site.
        #
        # Default:
        #     Current year.
        #
        # If status is supplied:
        #     Return only that status.
        # =====================================================================

        else:

            year = (
                filter_year
                or str(datetime.now().year)
            )

            statuses = (
                [filter_status.lower()]
                if filter_status
                else DEFAULT_STATUSES
            )

            # -------------------------------------------------------------
            # Full access
            # -------------------------------------------------------------

            if access_scope["full_access"]:

                data = get_store_job_metrics(
                    filter_year=year,
                    statuses=statuses,
                )

            # -------------------------------------------------------------
            # Restricted access
            # -------------------------------------------------------------

            else:

                scoped_location = (
                    access_scope["location"]
                )

                if not scoped_location:

                    return _response(
                        403,
                        {
                            "message":
                                "No location assigned"
                        },
                        HEADERS,
                    )

                data = get_store_job_metrics(
                    locations=[
                        scoped_location
                    ],
                    filter_year=year,
                    statuses=statuses,
                )

        # =====================================================================
        # IMPORTANT:
        #
        # Return ONLY the dictionary.
        #
        # The dashboard aggregator can add:
        #
        #     "storeJobs": <this response>
        # =====================================================================
        print("data:", json.dumps(data))
        return _response(
            200,
            data,
            HEADERS,
        )

    except Exception:

        traceback.print_exc()

        return _response(
            500,
            {
                "message":
                    "Failed to fetch job metrics"
            },
            HEADERS,
        )


0
