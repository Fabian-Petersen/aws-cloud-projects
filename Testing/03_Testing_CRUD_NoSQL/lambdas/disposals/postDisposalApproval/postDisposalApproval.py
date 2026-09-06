import boto3
import uuid
import json
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from shared_utils.delete_reminder_schedule import delete_reminder_schedule
from shared_utils._response import _response
from shared_utils.claims import get_requestor_identity
from shared_utils.cors import handle_options_request, handle_request_metadata
from shared_utils.dynamodb import normalize_string, query_first
from shared_utils.request import parse_json_body
from shared_utils.to_human_date import get_local_now

dynamodb = boto3.resource("dynamodb")

TABLE_NAME_DISPOSALS = "crud-nosql-app-assets-disposal-table"
table_disposals = dynamodb.Table(TABLE_NAME_DISPOSALS)

# ---------------------------------------------------------------------------- #
#                                Disposal by ID                                #
# ---------------------------------------------------------------------------- #


def get_disposal_by_id(disposal_id: str) -> dict | None:
    """Query the disposal partition and return its complete primary key."""
    return query_first(
        table_disposals,
        KeyConditionExpression=Key("disposalId").eq(disposal_id),
        ConsistentRead=True,
    )


def lambda_handler(event, context):
    print("event:", json.dumps(event))
    """
    Approve an asset disposal.

    This Lambda function approves an existing asset disposal. The frontend
    sends only the disposal ID and the status (`approved`). The backend
    records the approval metadata using the authenticated Cognito user's
    claims.

    On approval, the following fields are updated:
        - status
        - approvedBy
        - approvedBySub
        - approvedDate
        - approvalId
        - approvalReminderCount
        - approved
        - dateUpdated

    Args:
        event: API Gateway Lambda event containing:
            body:
                {
                    "id": "<disposal-id>",
                    "status": "approved"
                }

            requestContext.authorizer.claims:
                Authenticated Cognito user claims.

        context:
            Lambda runtime context.

    Returns:
        HTTP response containing the updated disposal.

    Response Codes:
        200 - Disposal approved successfully.
        400 - Invalid request.
        401 - Missing authenticated user.
        404 - Disposal not found.
        409 - Disposal changed during approval.
        500 - Internal server or database error.
    """

    method, headers = handle_request_metadata(
        event,
        allowed_methods="POST,PUT,OPTIONS",
    )
    options_response = handle_options_request(method, headers)
    if options_response:
        return options_response

    try:
        data = parse_json_body(event)
    except ValueError as exc:
        return _response(400, {"message": str(exc)}, headers)

    try:
        identity = get_requestor_identity(event)
        approved_by_sub = identity["requestorSub"]
        if not approved_by_sub:
            return _response(401, {"message": "Unauthorized"}, headers)

        disposal_id = data.get("id")
        status = normalize_string(data.get("status"))
        approvalId = str(uuid.uuid4())

        if not disposal_id:
            return _response(400, {"message": "Missing field: id"}, headers)

        if not isinstance(disposal_id, str) or not disposal_id.strip():
            return _response(400, {"message": "Invalid field: id"}, headers)

        if status != "approved":
            return _response(
                400,
                {"message": "Only the status 'approved' is supported."},
                headers,
            )

        disposal_item = get_disposal_by_id(disposal_id)
        if not disposal_item:
            return _response(404, {"message": "Disposal not found"}, headers)

        if disposal_item.get("status") != "pending":
            return _response(
                400,
                {"message": "Only pending disposals can be approved."},
                headers,
            )

        disposal_created = disposal_item["disposalCreated"]
        disposal_id = disposal_item["disposalId"]

        approved_by = identity["requestedBy"]

        approvedDate = get_local_now()

        response = table_disposals.update_item(
            Key={
                "disposalId": disposal_id,
                "disposalCreated": disposal_created,
            },
            UpdateExpression="""
                SET #status = :status,
                    approvalId = :approvalId,
                    approvedBy = :approvedBy,
                    approvedBySub = :approvedBySub,
                    approvedDate = :approvedDate,
                    approvalReminderCount = :approvalReminderCount,
                    #approved = :approved,
                    dateUpdated = :approvedDate
            """,
            ExpressionAttributeNames={
                "#status": "status",
                "#approved": "approved",
            },
            ExpressionAttributeValues={
                ":status": "approved",
                ":approvalId": approvalId,
                ":approvedBy": approved_by,
                ":approvedBySub": approved_by_sub,
                ":approvedDate": approvedDate,
                ":approvalReminderCount": 0,
                ":pending": "pending",
                ":approved": {
                    "approvalId": approvalId,
                    "approvedBy": approved_by,
                    "approvedBySub": approved_by_sub,
                    "approvedDate": approvedDate,
                },
            },
            ConditionExpression="""
            attribute_exists(disposalId)
            AND attribute_exists(disposalCreated)
            AND #status = :pending
            """,
            ReturnValues="ALL_NEW"
        )

        try:
            delete_reminder_schedule(
                disposal_item.get("schedule_name")
                or f"disposal-{disposal_id}-timeout"
            )
        except Exception as exc:
            # Approval is already committed; cleanup must not report it as failed.
            print("Disposal approved, but reminder cleanup failed:", exc)

        return _response(
            200,
            {
                "message": "Disposal approved successfully.",
                "data": response["Attributes"],
            },
            headers,
        )

    except ClientError as exc:
        error_code = exc.response["Error"]["Code"]

        if error_code == "ConditionalCheckFailedException":
            return _response(
                409,
                {"message": "Disposal no longer exists or is no longer pending."},
                headers,
            )

        print("DynamoDB Error:", exc)
        return _response(500, {"message": "Database error"}, headers)

    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": "Internal server error"}, headers)
