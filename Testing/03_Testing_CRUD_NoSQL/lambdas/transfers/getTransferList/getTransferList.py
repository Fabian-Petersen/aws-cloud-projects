"""
This function returns all the asset transfers in the asset transfers table. Admins and technicians can see all transfers, while regular users only see their own transfers/transfers of the location they belong to.

"""

import json
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Key
from datetime import datetime, timezone, timedelta

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("crud-nosql-app-assets-transfer-table")

VALID_STATUSES = {
    "pending",
    "approved",
    "rejected",
    "in-transit",
    "receipted",
    "cancelled"
}

# $ STAGES: Used to build the response object for the frontend
STAGES = {
    "request": [
        "requested_by",
        "requestor_name",
        "requestor_sub",
        "assetID",
        "area",
        "images",
        "equipment",
        "description",
        "transferReason",
        "locationFrom",
        "locationTo",
        "expectedDate",
    ],
    "approved": [
        "approvalId",
        "dateApproved",
        "approvedBy",
        "approvedBySub",
        "approvalReminderCount",
    ],
    "inTransit": [
        "transitId",
        "dateCreated",
        "inTransitSub",
        "transportType",
        "transportName",
        "transportDate",
        "trackingNumber",
        "transportNotes",
        "transportCost",
        "images",
        "invoices",
    ],
    "receipt": [
        "receiptId",
        "dateReceived",
        "receivedBySub",
        "condition",
        "damageDetails",
        "images",
        "deliveryNote",
    ],
    "cancelled": [
        "dateCancelled",
        "cancelledBySub",
        "cancelReason",
        "cancelStatus",
    ],
}

# $ Dates to be changed from ISO string to human readable date
DATE_FIELDS = {
    "transferCreated",
    "expectedDate",
    "dateApproved",
    "dateCreated",
    "transportDate",
    "dateReceived",
    "dateCancelled",
}

# ----------------------------
# Decimal serializer for DynamoDB types in JSON responses
# ----------------------------


def decimal_serializer(obj):
    """
    Custom JSON serializer for handling DynamoDB Decimal types.

    Args:
        obj: Object to serialize.

    Returns:
        int | float: Converted numeric value.

    Raises:
        TypeError: If object type is not supported.
    """
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    raise TypeError

# ----------------------------
# Date formatting in SAST for human readability
# ----------------------------


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


# ----------------------------
# Cognito groups parser for flexible group claim formats
# ----------------------------


def parse_groups(groups_claim):
    if not groups_claim:
        return []

    if isinstance(groups_claim, list):
        return [str(group).lower() for group in groups_claim]

    if isinstance(groups_claim, str):
        try:
            parsed = json.loads(groups_claim)
            if isinstance(parsed, list):
                return [str(group).lower() for group in parsed]
        except Exception:
            pass

        return [group.strip().lower() for group in groups_claim.split(",")]

    return []


# =========================================================================
# Format all the date fields in the STAGES
# =========================================================================


def format_dates(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if key in DATE_FIELDS and value:
                data[key] = to_human_date(value)
            else:
                format_dates(value)

    elif isinstance(data, list):
        for item in data:
            format_dates(item)


# =========================================================================
# Build the response object
# =========================================================================

def build_transfer_response(item):
    response = {
        "id": item["id"],
        "assetID": item["assetID"],
        "status": item["status"],
        "transferCreated": item["transferCreated"],
    }

    for stage, fields in STAGES.items():
        data = {}

        for field in fields:
            if field in item:
                data[field] = item[field]

        response[stage] = data or None

    return response

# ----------------------------
# GSI query (status-based)
# ----------------------------


def query_by_status(status):
    items = []

    response = table.query(
        IndexName="TransferStatusIndex",
        KeyConditionExpression=Key("status").eq(status),
        ScanIndexForward=False  # newest first
    )

    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = table.query(
            IndexName="TransferStatusIndex",
            KeyConditionExpression=Key("status").eq(status),
            ScanIndexForward=False,
            ExclusiveStartKey=response["LastEvaluatedKey"]
        )

        items.extend(response.get("Items", []))

    return items

# ----------------------------
# Scan fallback (no filters)
# ----------------------------


def scan_all():
    items = []
    response = table.scan()
    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = table.scan(
            ExclusiveStartKey=response["LastEvaluatedKey"]
        )
        items.extend(response.get("Items", []))

    return items


# ----------------------------
# Construct Headers
# ----------------------------

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


# ----------------------------
# Construct Options
# ----------------------------

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


# ----------------------------
# Lambda handler
# ----------------------------


def lambda_handler(event, context):
    print("event:", event)

    # Query params
    multi_query_params = event.get("multiValueQueryStringParameters") or {}
    statuses = (
        multi_query_params.get("status[]")
        or multi_query_params.get("status")
        or []
    )

    invalid = [status for status in statuses if status not in VALID_STATUSES]

    if invalid:
        return _response(400, {"message": f"Invalid status(es): {', '.join(invalid)}"}, HEADERS)

    # Auth claims
    claims = event.get("requestContext", {}).get(
        "authorizer", {}).get("claims", {})
    groups = parse_groups(claims.get("cognito:groups"))
    user_sub = claims.get("sub")

    # CORS
    method, HEADERS = handle_request_metadata(event)

    options_response = handle_options_request(method, HEADERS)
    if options_response:
        return options_response

    try:
        is_admin_or_technician = any(
            group in ["admin", "technician"] for group in groups)

        # ----------------------------
        # DATA FETCH LOGIC
        # ----------------------------

        if is_admin_or_technician:
            # ✅ USE GSI IF STATUS EXISTS
            if statuses:
                items = []

                for status in statuses:
                    items.extend(query_by_status(status))
            else:
                items = scan_all()

        else:
            # Non-admin users only see their own jobs
            if not user_sub:
                return _response(403, {"message": "User sub not found in token"}, HEADERS)

            if statuses:
                items = []
                # GSI + user filter fallback (no composite index)
                for status in statuses:
                    items.extend(query_by_status(status))
            else:
                items = scan_all()

            items = [item for item in items if item.get(
                "request_sub") == user_sub]

        # ----------------------------
        # Build response
        # ----------------------------

        response = []

        for item in items:
            transfer = build_transfer_response(item)
            format_dates(transfer)
            response.append(transfer)

        return _response(200, response, HEADERS)

    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": "Internal server error"}, HEADERS)


# ----------------------------
# Response helper
# ----------------------------
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
        "headers": headers,
        "body": json.dumps(body, default=decimal_serializer),
    }
