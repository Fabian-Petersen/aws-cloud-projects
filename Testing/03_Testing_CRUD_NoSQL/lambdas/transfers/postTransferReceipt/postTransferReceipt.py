import json
import boto3
from datetime import datetime, timezone, timedelta
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from botocore.config import Config

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client(
    "s3",
    region_name="af-south-1",
    config=Config(
        s3={"addressing_style": "virtual"},
        signature_version="s3v4",
        region_name="af-south-1"
    )
)

TABLE_NAME_TRANSFERS = "crud-nosql-app-assets-transfer-table"
table_transfers = dynamodb.Table(TABLE_NAME_TRANSFERS)

BUCKET_NAME = "crud-nosql-app-images"

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
        transit_id: The unique transfer ID.

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


def generate_presigned_files(
    transfer_id: str,
    folder: str,
    files: list[dict]
):
    urls = []

    for file_info in files:
        filename = file_info["filename"]
        content_type = file_info.get(
            "content_type",
            "application/octet-stream"
        )

        key = f"transfers/{transfer_id}/{folder}/{filename}"

        url = s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": BUCKET_NAME,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=3600,
        )

        if "s3.af-south-1.amazonaws.com" not in url:
            raise Exception(
                "Presigned URL generated with incorrect S3 endpoint")

        urls.append({
            "filename": filename,
            "key": key,
            "url": url,
            "content_type": content_type,
        })

    return urls


def lambda_handler(event, context):
    """
    Set an asset transfer receipted (asset received).

    The lambda is triggered with path: `/transfers/0bdc65f2-c66a-4f9b-8a59-8c78845131d0/receipt`

    On receipt, the following fields are updated:
        - receiptId
        - dateReceived
        - deliveryNote
        - receiptNotes
        - receiptSub
        - receiptBy
        - receiptCondition
        - status
        - receiptIimages

    Args:
        event: API Gateway Lambda event containing:
            body:
                {
                    "condition" : "courier",
                    "receiptDate" : "2026-07-08T09:26",
                    "deliveryNote" : []
                    "images" : [],
                    "receiptNotes" : "asset received in good order.",
                    "status":"receipted"
                }
            requestContext.authorizer.claims:
                Authenticated Cognito user claims.

        context:
            Lambda runtime context.

    Returns:
        HTTP response containing the updated transfer.

    Response Codes:
        200 - Transfer receipt successfull.
        400 - Invalid request.
        409 - Transfer is no longer in in-transit state.
        500 - Internal server or database error.
    """

    try:
        print("event:", event)
        if not event.get("body"):
            return _response(400, {"message": "Missing request body"})

        data = json.loads(event["body"])

        # $ Validate required fields (assetID and description is not required)
        required_fields = ["condition", "receiptDate"]
        for field in required_fields:
            if not data.get(field):
                return _response(400, {"message": f"Missing or empty field: {field}"})

        claims = (
            event.get("requestContext", {})
            .get("authorizer", {})
            .get("claims", {})
        )
        # $ Get transfer_id from the pathParameters in the path
        transfer_id = event.get("pathParameters", {}).get("id")
        # $ Get the status from the action in the path
        status = normalize_string(data.get("status"))

        if not transfer_id:
            return _response(400, {"message": "Missing transfer id"})

        if status != "receipt":
            return _response(
                400,
                {"message": "Only the status 'receipt' is supported."}
            )

        transfer_item = get_transfer_by_id(transfer_id)

        if not transfer_item:
            return _response(404, {"message": "Transfer not found"})

        if normalize_string(transfer_item.get("status")) != "in-transit":
            return _response(400, {"message": "Only in-transit transfers can be moved receipted."})

        transfer_created = transfer_item["transferCreated"]
        asset_id = transfer_item["assetID"]

        receiptSub = claims.get("sub", "")
        receiptBy = f'{claims.get("name", "")} {claims.get("family_name", "")}'
        dateCreated = get_local_now()

        image_urls = generate_presigned_files(
            transfer_id,
            "receiptImages",
            data.get("images", [])
        )

        deliveryNote_urls = generate_presigned_files(
            transfer_id,
            "deliveryNote",
            data.get("deliveryNote", [])
        )

        response = table_transfers.update_item(
            Key={
                "assetID": asset_id,
                "transferCreated": transfer_created,
            },
            UpdateExpression="""
                SET #status = :status,
                    dateCreated = :dateCreated,
                    receiptSub = :receiptSub,
                    receiptBy = :receiptBy,
                    receiptDate = :receiptDate,
                    receiptCondition = :receiptCondition,
                    receiptNotes = :receiptNotes,
                    receiptImages = :receiptImages,
                    deliveryNote = :deliveryNote
            """,
            ExpressionAttributeNames={
                "#status": "status",
            },
            ExpressionAttributeValues={
                ":in-transit": "in-transit",
                ":status": "receipted",
                ":dateCreated": dateCreated,
                ":receiptSub": receiptSub,
                ":receiptBy": receiptBy,
                ":receiptDate": data["receiptDate"],
                ":receiptCondition": data["condition"],
                ":receiptNotes": data.get("receiptNotes", ""),
                ":receiptImages": [],
                ":deliveryNote": []
            },
            ConditionExpression="""
            attribute_exists(assetID) 
            AND attribute_exists(transferCreated)
            AND #status = :in-transit
            """,
            ReturnValues="ALL_NEW"
        )
        return _response(
            200,
            {
                "message": "Transfer receipt successfully.",
                "uploadUrls": {
                    "images": image_urls,
                    "deliveryNote": deliveryNote_urls
                }
            },
        )

    except ClientError as exc:
        error_code = exc.response["Error"]["Code"]

        if error_code == "ConditionalCheckFailedException":
            return _response(409, {"message": "Transfer is no longer in-transit state."})

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
