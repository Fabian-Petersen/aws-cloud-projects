import json

import boto3
from boto3.dynamodb.conditions import Key
from botocore.config import Config
from botocore.exceptions import ClientError


TABLE_NAME = "crud-nosql-app-maintenance-request-table"
BUCKET = "crud-nosql-app-images"
MISSING_OBJECT_CODES = {"404", "NoSuchKey", "NotFound"}

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client(
    "s3",
    region_name="af-south-1",
    config=Config(
        s3={"addressing_style": "virtual"},
        signature_version="s3v4",
        region_name="af-south-1",
    ),
)
table = dynamodb.Table(TABLE_NAME)

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Access-Control-Allow-Headers": (
        "Content-Type,Authorization,X-Amz-Date,X-Api-Key,"
        "X-Amz-Security-Token,X-Requested-With"
    ),
    "Access-Control-Allow-Credentials": "true",
}


def log_event(stage: str, **details) -> None:
    print(json.dumps({"stage": stage, **details}, default=str))


def get_request_by_action_id(action_id: str) -> dict | None:
    """Resolve an action ID to its maintenance request via ActionIdIndex."""
    response = table.query(
        IndexName="ActionIdIndex",
        KeyConditionExpression=Key("action_id").eq(action_id),
        Limit=1,
    )
    items = response.get("Items", [])
    return items[0] if items else None


def lambda_handler(event, context):
    action_id = str(
        (event.get("pathParameters") or {}).get("id") or ""
    ).strip()

    if not action_id:
        return _response(
            400,
            {
                "success": False,
                "code": "ACTION_ID_REQUIRED",
                "message": "Missing action id.",
            },
        )

    log_event("JOBCARD_DOWNLOAD_REQUESTED", action_id=action_id)

    try:
        item = get_request_by_action_id(action_id)
        if not item:
            log_event(
                "JOBCARD_NOT_FOUND",
                action_id=action_id,
                reason="maintenance_request_not_found",
            )
            return _response(
                404,
                {
                    "success": False,
                    "code": "REQUEST_NOT_FOUND",
                    "message": (
                        "No maintenance request was found for the action id."
                    ),
                },
            )

        request_id = str(item.get("id") or "").strip()
        if not request_id:
            log_event(
                "JOBCARD_NOT_FOUND",
                action_id=action_id,
                reason="request_id_missing",
            )
            return _response(
                404,
                {
                    "success": False,
                    "code": "REQUEST_NOT_FOUND",
                    "message": "The matched maintenance request has no id.",
                },
            )

        jobcard_number = item.get("jobcardNumber") or "jobcard"
        key = f"jobcards/{request_id}.pdf"

        try:
            s3.head_object(Bucket=BUCKET, Key=key)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code in MISSING_OBJECT_CODES:
                log_event(
                    "JOBCARD_NOT_FOUND",
                    request_id=request_id,
                    action_id=action_id,
                    jobcardNumber=jobcard_number,
                    pdf_s3_key=key,
                    reason="pdf_not_generated",
                )
                return _response(
                    404,
                    {
                        "success": False,
                        "code": "JOBCARD_NOT_GENERATED",
                        "message": (
                            "The jobcard PDF has not yet been generated."
                        ),
                    },
                )
            raise

        url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": BUCKET,
                "Key": key,
                "ResponseContentType": "application/pdf",
                "ResponseContentDisposition": (
                    f'attachment; filename="{jobcard_number}.pdf"'
                ),
            },
            ExpiresIn=600,
        )

        log_event(
            "JOBCARD_PRESIGNED_URL_CREATED",
            request_id=request_id,
            action_id=action_id,
            jobcardNumber=jobcard_number,
            pdf_s3_key=key,
        )
        return _response(200, {"jobcard_url": url})

    except ClientError as exc:
        log_event(
            "JOBCARD_DOWNLOAD_FAILED",
            action_id=action_id,
            error_code=exc.response.get("Error", {}).get("Code"),
            error=str(exc),
        )
        return _response(
            500,
            {
                "success": False,
                "code": "JOBCARD_DOWNLOAD_FAILED",
                "message": "Unable to create the jobcard download link.",
            },
        )
    except Exception as exc:
        log_event(
            "JOBCARD_DOWNLOAD_FAILED",
            action_id=action_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return _response(
            500,
            {
                "success": False,
                "code": "JOBCARD_DOWNLOAD_FAILED",
                "message": "Unable to create the jobcard download link.",
            },
        )


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": HEADERS,
        "body": json.dumps(body),
    }
