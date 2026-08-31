import json
import boto3
import uuid
from datetime import datetime, timezone, timedelta
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

TABLE_NAME = "crud-nosql-app-assets-transfer-table"
BUCKET_NAME = "crud-nosql-app-images"
table = dynamodb.Table(TABLE_NAME)

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Credentials": "true"
}

# $ Change the date format in the database to readible for humans


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


def normalize_string(value: str | None) -> str:
    return str(value or "").strip().lower()


def lambda_handler(event, context):
    print("event:", json.dumps(event))
    try:
        if not event.get("body"):
            return _response(400, {"message": "Missing request body"})

        data = json.loads(event["body"])

        claims = (
            event.get("requestContext", {})
            .get("authorizer", {})
            .get("claims", {})
        )

        # ------------------------------------------------------------------
        # Validate transfer
        # ------------------------------------------------------------------

        required_fields = [
            "transferReason",
            "locationFrom",
            "locationTo",
            "expectedDate",
            "assets",
        ]

        for field in required_fields:
            if not data.get(field):
                return _response(
                    400,
                    {"message": f"Missing or empty field: {field}"}
                )

        if not isinstance(data["assets"], list) or len(data["assets"]) == 0:
            return _response(
                400,
                {"message": "At least one asset is required"}
            )

        # ------------------------------------------------------------------
        # Metadata
        # ------------------------------------------------------------------

        sast = timezone(timedelta(hours=2))
        now = datetime.now(sast).isoformat()

        transfer_id = str(uuid.uuid4())

        user_id = claims.get("sub")
        user_name = claims.get("name", "")
        requested_by = (
            f'{claims.get("name", "")} '
            f'{claims.get("family_name", "")}'
        )
        user_email = claims.get("email")

        presigned_urls = []

        # ------------------------------------------------------------------
        # Transfer invoices URL
        # ------------------------------------------------------------------

        for file_info in data.get("transportInvoices", []):

            filename = file_info.get("filename")
            if not filename:
                continue

            content_type = file_info.get(
                "content_type",
                "application/octet-stream",
            )

            key = (
                f"transfers/{transfer_id}/"
                f"invoices/{filename}"
            )

            url = s3.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": BUCKET_NAME,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=3600,
            )

            presigned_urls.append({
                "type": "invoices",
                "filename": filename,
                "url": url,
                "key": key,
                "content_type": content_type
            })

        # ------------------------------------------------------------------
        # Assets & Images URL
        # ------------------------------------------------------------------

        processed_assets = []

        for asset_index, asset in enumerate(data["assets"]):

            for file_info in asset.get("images", []):

                filename = file_info.get("filename")
                if not filename:
                    continue

                content_type = file_info.get(
                    "content_type",
                    "application/octet-stream",
                )

                key = (
                    f"transfers/{transfer_id}/"
                    f"assets/{asset_index}/"
                    f"images/{filename}"
                )

                url = s3.generate_presigned_url(
                    "put_object",
                    Params={
                        "Bucket": BUCKET_NAME,
                        "Key": key,
                        "ContentType": content_type,
                    },
                    ExpiresIn=3600,
                )

                presigned_urls.append({
                    "type": "images",
                    "assetIndex": asset_index,
                    "assetID": asset.get("assetID"),
                    "filename": filename,
                    "content_type": content_type,
                    "url": url,
                    "key": key,
                })

            processed_assets.append({
                "assetIndex": asset_index,
                "assetID": asset.get("assetID"),
                "area": normalize_string(asset.get("area")),
                "equipment": asset.get("equipment"),
                "assetIssueReason": normalize_string(
                    asset.get("assetIssueReason")
                ),
                "assetIssueDetails": asset.get(
                    "assetIssueDetails",
                    "",
                ),
                "images": [],
            })

        # ------------------------------------------------------------------
        # Save transfer
        # ------------------------------------------------------------------

        item = {
            "transferId": transfer_id,
            "transferCreated": now,
            "transportInvoices": [],
            "status": "pending",
            "dateUpdated": now,

            "requested_by": normalize_string(requested_by),
            "requestor_sub": user_id,
            "requestor_email": user_email,
            "requestor_name": normalize_string(user_name),

            "approval_reminder_count": 0,
            "schedule_name": f"transfer-{transfer_id}-timeout",

            "transferReason": data["transferReason"],
            "locationFrom": normalize_string(data["locationFrom"]),
            "locationTo": normalize_string(data["locationTo"]),
            "expectedDate": data["expectedDate"],
            "description": data.get("description", ""),

            "assets": processed_assets,
        }

        table.put_item(Item=item)

        return _response(
            200,
            {
                "data": item,
                "presigned_urls": presigned_urls,
            },
        )

    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": "Internal server error"})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": HEADERS,
        "body": json.dumps(body),
    }


# Run the lambda locally with the events.json file to test
if __name__ == "__main__":
    with open("event.json") as f:
        event = json.load(f)

    result = lambda_handler(event, None)
    print(json.dumps(result, indent=2))
