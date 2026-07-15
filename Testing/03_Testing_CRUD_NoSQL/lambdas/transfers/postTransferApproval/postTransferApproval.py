import json
import boto3
import uuid
from datetime import datetime, timezone, timedelta
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")

TABLE_NAME_TRANSFERS = "crud-nosql-app-assets-transfer-table"
table_transfers = dynamodb.Table(TABLE_NAME_TRANSFERS)

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "POST,PUT,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With",
    "Access-Control-Allow-Credentials": "true"
}


def get_local_now() -> str:
    """
    Return the current date and time in South Africa as an ISO 8601 string.

    Returns:
        An ISO 8601 formatted datetime string with the South Africa
        (UTC+02:00) timezone offset.

    Example:
        2026-07-06T20:57:46.123456+02:00
    """
    utc_now = datetime.now(timezone.utc)
    local_time = utc_now.astimezone(timezone(timedelta(hours=2)))
    return local_time.isoformat()


def get_transfer_by_id(transfer_id: str) -> dict | None:
    """
    Retrieve an asset transfer using the IdIndex global secondary index.

    The asset transfers table uses `assetID` as the partition key and
    `transferCreated` as the sort key. Since the frontend only provides the
    unique transfer `id`, this function queries the `IdIndex` GSI to locate
    the transfer and returns the complete item, including the primary key
    attributes required for updates.

    Args:
        transfer_id: The unique transfer ID.

    Returns:
        The transfer item if found, otherwise None.
    """

    response = table_transfers.query(
        IndexName="IdIndex",
        KeyConditionExpression=Key("id").eq(transfer_id),
        Limit=1,
    )

    items = response.get("Items", [])
    return items[0] if items else None


def normalize_string(value: str | None) -> str:
    return str(value or "").strip().lower()


def lambda_handler(event, context):
    """
    Approve an asset transfer.

    This Lambda function approves an existing asset transfer. The frontend
    sends only the transfer ID and the status (`approved`). The backend
    records the approval metadata using the authenticated Cognito user's
    claims.

    On approval, the following fields are updated:
        - status
        - approvedBy
        - approvedBySub
        - approvedDate

    Args:
        event: API Gateway Lambda event containing:
            body:
                {
                    "id": "<transfer-id>",
                    "status": "approved"
                }

            requestContext.authorizer.claims:
                Authenticated Cognito user claims.

        context:
            Lambda runtime context.

    Returns:
        HTTP response containing the updated transfer.

    Response Codes:
        200 - Transfer approved successfully.
        400 - Invalid request.
        404 - Transfer not found.
        500 - Internal server or database error.
    """

    try:
        if not event.get("body"):
            return _response(400, {"message": "Missing request body"})

        data = json.loads(event["body"])

        claims = (
            event.get("requestContext", {})
            .get("authorizer", {})
            .get("claims", {})
        )

        transfer_id = data.get("id")
        status = normalize_string(data.get("status"))
        approvalId = str(uuid.uuid4())

        if not transfer_id:
            return _response(400, {"message": "Missing field: id"})

        if status != "approved":
            return _response(
                400,
                {"message": "Only the status 'approved' is supported."}
            )

        transfer_item = get_transfer_by_id(transfer_id)
        if normalize_string(transfer_item.get("status")) != "pending":
            return _response(400, {"message": "Only pending transfers can be approved."})

        if not transfer_item:
            return _response(404, {"message": "Transfer not found"})

        transfer_created = transfer_item["transferCreated"]
        asset_id = transfer_item["assetID"]

        approved_by = (
            f'{claims.get("name", "").strip()} '
            f'{claims.get("family_name", "").strip()}'
        ).strip()

        approved_by_sub = claims.get("sub", "")

        approvedDate = get_local_now()

        response = table_transfers.update_item(
            Key={
                "assetID": asset_id,
                "transferCreated": transfer_created,
            },
            UpdateExpression="""
                SET #status = :status,
                    approvalId = :approvalId,
                    approvedBy = :approvedBy,
                    approvedBySub = :approvedBySub,
                    approvedDate = :approvedDate,
                    approvalReminderCount = :approvalReminderCount
            """,
            ExpressionAttributeNames={
                "#status": "status",
            },
            ExpressionAttributeValues={
                ":status": "approved",
                ":approvalId": approvalId,
                ":approvedBy": approved_by,
                ":approvedBySub": approved_by_sub,
                ":approvedDate": approvedDate,
                ":approvalReminderCount": 0
            },
            ConditionExpression="""
            attribute_exists(assetID) 
            AND attribute_exists(transferCreated) 
            AND #status <> :status
            """,
            ReturnValues="ALL_NEW"
        )
        return _response(
            200,
            {
                "message": "Transfer approved successfully.",
                "data": response["Attributes"],
            },
        )

    except ClientError as exc:
        error_code = exc.response["Error"]["Code"]

        if error_code == "ConditionalCheckFailedException":
            return _response(404, {"message": "Transfer not found"})

        print("DynamoDB Error:", exc)
        return _response(500, {"message": "Database error"})

    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": "Internal server error"})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": HEADERS,
        "body": json.dumps(body),
    }
