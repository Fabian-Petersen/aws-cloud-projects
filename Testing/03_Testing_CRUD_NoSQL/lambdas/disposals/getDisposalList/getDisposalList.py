"""Return disposal requests visible to the authenticated user."""

import json

import boto3
from boto3.dynamodb.conditions import Key

from shared_utils._response import _response
from shared_utils.claims import get_user_claims, parse_groups
from shared_utils.cors import handle_options_request, handle_request_metadata
from shared_utils.dynamodb import normalize_string, query_all, scan_all
from shared_utils.to_human_date import format_dates


DISPOSAL_TABLE_NAME = "crud-nosql-app-assets-disposal-table"
VALID_STATUSES = {
    "pending",
    "approved",
    "rejected",
    "expired",
    "cancelled",
    "disposed",
}
STAGES = {
    "pending": [
        "requestedBy",
        "requestorName",
        "requestorSub",
        "description",
        "disposalReason",
        "location",
        "expectedDisposalDate",
    ],
    "approved": [
        "approvalId",
        "approvedDate",
        "approvedBy",
        "approvedBySub",
        "approvalReminderCount",
    ],
    "disposed": [
        "disposalId",
        "disposedDate",
        "disposedBy",
        "disposedBySub",
        "disposalMethod",
        "disposalLocation",
        "disposalCost",
        "disposalNotes",
        "disposalImages",
        "disposalDocuments",
    ],
    "cancelled": [
        "cancelledDate",
        "cancelledBy",
        "cancelledBySub",
        "cancelReason",
    ],
    "rejected": [
        "rejectedDate",
        "rejectedBy",
        "rejectedBySub",
        "rejectionReason",
    ],
    "expired": ["expiredDate", "reason"],
}
DATE_TIME_FIELDS = {
    "disposalCreated",
    "approvedDate",
    "disposedDate",
    "cancelledDate",
    "rejectedDate",
    "expiredDate",
}
DATE_FIELDS = {"expectedDisposalDate"}

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DISPOSAL_TABLE_NAME)


def _requested_statuses(event):
    """Return normalized status filters from API Gateway query parameters."""
    multi_value = event.get("multiValueQueryStringParameters") or {}
    statuses = multi_value.get("status[]") or multi_value.get("status")
    if statuses is None:
        single_value = event.get("queryStringParameters") or {}
        statuses = single_value.get("status[]") or single_value.get("status")
    if statuses is None:
        return []
    if not isinstance(statuses, list):
        statuses = [statuses]
    return [normalize_string(status) for status in statuses if str(status).strip()]


def _build_disposal_response(item):
    """Build the progressive-enrichment response expected by the frontend."""
    response = {
        "id": item["disposalId"],
        "disposalCreated": item["disposalCreated"],
        "status": item["status"],
        "assets": item.get("assets", []),
    }
    for stage, fields in STAGES.items():
        stored_stage = item.get(stage)
        source = stored_stage if isinstance(stored_stage, dict) else item
        stage_data = {field: source[field] for field in fields if field in source}
        response[stage] = stage_data or None
    format_dates(response, DATE_TIME_FIELDS, DATE_FIELDS)
    return response


def _query_by_status(status):
    """Return every disposal matching a status, newest request first."""
    return query_all(
        table,
        IndexName="DisposalStatusIndex",
        KeyConditionExpression=Key("status").eq(status),
        ScanIndexForward=False,
    )


def lambda_handler(event, context):
    """List filtered disposal requests according to Cognito group visibility."""
    print("event:", json.dumps(event))

    method, headers = handle_request_metadata(event, allowed_methods="GET,OPTIONS")
    options_response = handle_options_request(method, headers)
    if options_response:
        return options_response

    statuses = _requested_statuses(event)
    invalid_statuses = [status for status in statuses if status not in VALID_STATUSES]
    if invalid_statuses:
        return _response(
            400,
            {"message": f"Invalid status(es): {', '.join(invalid_statuses)}"},
            headers,
        )

    claims = get_user_claims(event)
    groups = parse_groups(claims.get("cognito:groups"))
    requestor_sub = claims.get("sub")

    try:
        if statuses:
            items = []
            for status in statuses:
                items.extend(_query_by_status(status))
        else:
            items = scan_all(table)
            items.sort(
                key=lambda item: item.get("disposalCreated", ""),
                reverse=True,
            )

        is_privileged = any(
            group in {"admin", "technician"} for group in groups
        )
        if not is_privileged:
            if not requestor_sub:
                return _response(
                    403,
                    {"message": "User sub not found in token"},
                    headers,
                )
            items = [
                item
                for item in items
                if item.get("requestorSub") == requestor_sub
            ]

        response = [_build_disposal_response(item) for item in items]
        return _response(200, response, headers)
    except Exception as exc:
        print("Error listing disposal requests:", repr(exc))
        return _response(500, {"message": "Internal server error"}, headers)
