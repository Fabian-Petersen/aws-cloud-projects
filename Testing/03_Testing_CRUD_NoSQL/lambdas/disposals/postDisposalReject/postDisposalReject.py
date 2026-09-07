import boto3
import uuid
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from shared_utils._response import _response
from shared_utils.claims import get_requestor_identity, get_user_claims, parse_groups
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
    """Reject a pending disposal using body fields id, status and reason.

    Only authenticated members of the Admin Cognito group may reject requests.
    The reason is a non-empty string and retains its original capitalization.
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
        rejected_by_sub = identity["requestorSub"]
        if not rejected_by_sub:
            return _response(401, {"message": "Unauthorized"}, headers)

        groups = parse_groups(get_user_claims(event).get("cognito:groups"))
        if "admin" not in groups:
            return _response(403, {"message": "Only administrators can reject disposal requests."}, headers)

        reason = data.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            return _response(400, {"message": "A non-empty rejection reason is required."}, headers)
        reason = reason.strip()

        disposal_id = data.get("id")
        status = normalize_string(data.get("status"))
        rejectedId = str(uuid.uuid4())

        if not disposal_id:
            return _response(400, {"message": "Missing field: id"}, headers)

        if not isinstance(disposal_id, str) or not disposal_id.strip():
            return _response(400, {"message": "Invalid field: id"}, headers)

        if status != "rejected":
            return _response(
                400,
                {"message": "Only the status 'rejected' is supported."},
                headers,
            )

        disposal_item = get_disposal_by_id(disposal_id.strip())
        if not disposal_item:
            return _response(404, {"message": "Disposal not found"}, headers)

        if disposal_item.get("status") != "pending":
            return _response(
                400,
                {"message": "Only pending disposals can be rejected."},
                headers,
            )

        disposal_created = disposal_item["disposalCreated"]
        disposal_id = disposal_item["disposalId"]

        rejected_by = identity["requestedBy"]

        rejectedDate = get_local_now()

        response = table_disposals.update_item(
            Key={
                "disposalId": disposal_id,
                "disposalCreated": disposal_created,
            },
            UpdateExpression="""
                SET #status = :status,
                    rejectedId = :rejectedId,
                    rejectedBy = :rejectedBy,
                    rejectedBySub = :rejectedBySub,
                    rejectedDate = :rejectedDate,
                    rejectionReason = :rejectionReason,
                    #rejected = :rejected,
                    dateUpdated = :rejectedDate
            """,
            ExpressionAttributeNames={
                "#status": "status",
                "#rejected": "rejected",
            },
            ExpressionAttributeValues={
                ":status": "rejected",
                ":rejectedId": rejectedId,
                ":rejectedBy": rejected_by,
                ":rejectedBySub": rejected_by_sub,
                ":rejectedDate": rejectedDate,
                ":rejectionReason": reason,
                ":pending": "pending",
                ":rejected": {
                    "rejectedId": rejectedId,
                    "rejectionReason": reason,
                    "rejectedBy": rejected_by,
                    "rejectedBySub": rejected_by_sub,
                    "rejectedDate": rejectedDate,
                },
            },
            ConditionExpression="""
            attribute_exists(disposalId)
            AND attribute_exists(disposalCreated)
            AND #status = :pending
            """,
            ReturnValues="ALL_NEW"
        )

        return _response(
            200,
            {
                "message": "Disposal rejected successfully.",
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
