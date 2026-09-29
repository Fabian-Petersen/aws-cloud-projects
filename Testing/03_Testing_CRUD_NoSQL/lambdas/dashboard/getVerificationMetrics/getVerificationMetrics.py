
import boto3
import json
import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")

assets_table = dynamodb.Table("crud-nosql-app-assets-table")
users_table = dynamodb.Table("crud-nosql-app-users-table")

# How many days out counts as "Due" rather than comfortably "Verified"
DUE_SOON_DAYS = int(os.environ.get("DUE_SOON_DAYS", 30))

# Attribute names in the users table.
USER_SUB_ATTRIBUTE = os.environ.get("USER_SUB_ATTRIBUTE", "sub")
USER_LOCATION_ATTRIBUTE = os.environ.get("USER_LOCATION_ATTRIBUTE", "location")

ADMIN_GROUP = os.environ.get("ADMIN_GROUP", "admin")

# ---------------------------------------------------------------------------- #
#                           Serialise Decimal Values                           #
# ---------------------------------------------------------------------------- #


def decimal_serializer(obj):
    """
    Convert DynamoDB Decimal values into JSON-compatible numbers.
    """
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)

        return float(obj)

    raise TypeError


# ---------------------------------------------------------------------------- #
#                                Handle API CORS                               #
# ---------------------------------------------------------------------------- #


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


# ---------------------------------------------------------------------------- #
#                                Parse ISO date                                #
# ---------------------------------------------------------------------------- #

def parse_iso(date_str):
    """
    Parse an ISO8601 string with or without an offset
    into an aware datetime.
    """
    if not date_str:
        return None

    try:
        dt = datetime.fromisoformat(date_str)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt

    except ValueError:
        return None

# ---------------------------------------------------------------------------- #
#                                Get User Claims                               #
# ---------------------------------------------------------------------------- #


def get_user_claims(event):
    """
    Extract Cognito JWT claims from the API Gateway request.

    Supports the HTTP API JWT authorizer structure:

        event["requestContext"]["authorizer"]["jwt"]["claims"]
    """
    return (
        event
        .get("requestContext", {})
        .get("authorizer", {})
        .get("claims", {})
    )

# ---------------------------------------------------------------------------- #
#                                Get User Group                                #
# ---------------------------------------------------------------------------- #


def get_user_groups(claims):
    """
    Return the Cognito groups associated with the signed-in user.

    Cognito can return the groups claim as either a space-separated
    string or another iterable representation.
    """
    groups = claims.get("cognito:groups", "")

    if isinstance(groups, str):
        return [
            group.strip()
            for group in groups.split(",")
            if group.strip()
        ]

    if isinstance(groups, list):
        return groups

    return []

# ---------------------------------------------------------------------------- #
#                           Get Selected Location from Frontend                #
# ---------------------------------------------------------------------------- #


def get_requested_location(event):
    """
    Get the optional location selected by the frontend.

    This value is only relevant for administrators.
    """
    query_params = event.get("queryStringParameters") or {}

    location = query_params.get("location")

    if not location:
        return None

    return location.strip()

# ---------------------------------------------------------------------------- #
#                               Get User Location                              #
# ---------------------------------------------------------------------------- #


def get_user_location(claims):
    """
    Retrieve the signed-in user's location from the users table.

    The Cognito `sub` matches the users table `id` partition key.
    """
    user_sub = claims.get("sub")

    if not user_sub:
        raise ValueError(
            "Authenticated user does not contain a Cognito sub"
        )

    response = users_table.get_item(
        Key={
            "id": user_sub
        },
        ProjectionExpression="#location",
        ExpressionAttributeNames={
            "#location": "location"
        },
    )

    user = response.get("Item")

    if not user:
        raise ValueError(
            f"User {user_sub} was not found in the users table"
        )

    location = user.get("location")

    if not location:
        raise ValueError(
            f"User {user_sub} does not have a location"
        )

    return location

# ---------------------------------------------------------------------------- #
#                                   Get data                                   #
# ---------------------------------------------------------------------------- #


def get_data_scope(event):
    """
    Determine which location(s) the signed-in user is allowed to see.

    Administrators:
        - No location parameter -> all sites
        - location parameter -> selected site

    Non-administrators:
        - Always restricted to their users-table location
        - Any frontend location parameter is ignored
    """
    claims = get_user_claims(event)
    print("claims:", claims)
    groups = get_user_groups(claims)
    print("groups:", groups)
    requested_location = get_requested_location(event)

    is_admin = ADMIN_GROUP in groups

    if is_admin:
        return {
            "is_admin": True,
            "location": requested_location,
        }

    user_location = get_user_location(claims)

    return {
        "is_admin": False,
        "location": user_location,
    }

# ---------------------------------------------------------------------------- #
#                               Get All locations                              #
# ---------------------------------------------------------------------------- #


def normalize_location(value):
    """Return a canonical location value for reliable comparisons.

    Location values were historically stored with inconsistent casing and
    whitespace.  Keep the original value for display, but compare a collapsed,
    case-insensitive representation so values such as ``Golden Acre`` and
    `` golden  acre `` refer to the same site.
    """
    return " ".join(str(value or "").split()).casefold()


def scan_all_items(location=None):
    """
    Scan asset verification data.

    If location is provided, only assets belonging to that
    location are returned.

    If location is None, all sites are returned.
    """
    items = []

    projection_expression = (
        "verify_status, "
        "next_verification_due, "
        "last_verified_at, "
        "#location"
    )

    expression_attribute_names = {
        "#location": "location"
    }

    scan_kwargs = {
        "ProjectionExpression": projection_expression,
        "ExpressionAttributeNames": expression_attribute_names,
    }

    normalized_location = normalize_location(location)

    while True:
        response = assets_table.scan(**scan_kwargs)

        page_items = response.get("Items", [])

        if normalized_location:
            page_items = [
                item
                for item in page_items
                if normalize_location(item.get("location"))
                == normalized_location
            ]

        items.extend(page_items)

        last_key = response.get("LastEvaluatedKey")

        if not last_key:
            break

        scan_kwargs["ExclusiveStartKey"] = last_key

    return items


def classify_status(item, now, due_soon_cutoff):
    """
    Classify an asset's verification state.
    """
    verify_status = (
        item.get("verify_status") or ""
    ).lower()

    last_verified_at = item.get("last_verified_at")

    next_due = parse_iso(
        item.get("next_verification_due")
    )

    # Never verified at all
    if verify_status != "verified" or not last_verified_at:
        return "Not Verified"

    # Verified, but no due date on record
    if next_due is None:
        return "Verified"

    if next_due < now:
        return "Overdue"

    if next_due <= due_soon_cutoff:
        return "Due"

    return "Verified"


def lambda_handler(event, context):
    print(
        "event:",
        json.dumps(
            event,
            default=decimal_serializer
        )
    )

    # ---------------------------------------------------------------------------- #
    #                                     CORS                                     #
    # ---------------------------------------------------------------------------- #
    method, HEADERS = handle_request_metadata(event)

    options_response = handle_options_request(method, HEADERS)
    if options_response:
        return options_response

    try:
        # ---------------------------------------------------------------------------- #
        #                 1. Determine the user's permitted data scope                 #
        # ---------------------------------------------------------------------------- #

        scope = get_data_scope(event)

        location = scope["location"]
        is_admin = scope["is_admin"]

        print(
            "Dashboard verification scope:",
            json.dumps(
                {
                    "is_admin": is_admin,
                    "location": location,
                }
            )
        )

        # ---------------------------------------------------------
        # 2. Retrieve assets for the permitted location
        # ---------------------------------------------------------

        items = scan_all_items(location)

        now = datetime.now(timezone.utc)

        due_soon_cutoff = (
            now + timedelta(days=DUE_SOON_DAYS)
        )

        # ---------------------------------------------------------
        # 3. Calculate verification status
        # ---------------------------------------------------------

        status_counts = {
            "Verified": 0,
            "Due": 0,
            "Overdue": 0,
            "Not Verified": 0,
        }

        for item in items:
            status = classify_status(
                item,
                now,
                due_soon_cutoff,
            )

            status_counts[status] += 1

        total = len(items)

        verified = status_counts["Verified"]

        compliance = (
            round((verified / total) * 100)
            if total > 0
            else 0
        )

        # ---------------------------------------------------------
        # 4. Build response
        # ---------------------------------------------------------

        verification_data = {
            "location": location if location else "all sites",
            "compliance": compliance,
            "total": total,
            "statuses": [
                {
                    "name": label,
                    "value": status_counts[label],
                }
                for label in [
                    "Verified",
                    "Due",
                    "Overdue",
                    "Not Verified",
                ]
            ],
        }

        return _response(200, verification_data, HEADERS)

    except Exception as e:
        print(
            f"Error fetching asset verification metrics: {e}"
        )

        return _response(
            500,
            {
                "error": "Failed to fetch asset verification metrics"
            },
            HEADERS,
        )

# ---------------------------------------------------------------------------- #
#                                Response helper                               #
# ---------------------------------------------------------------------------- #


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
        "body": json.dumps(body, default=decimal_serializer),
        "headers": headers,
    }
