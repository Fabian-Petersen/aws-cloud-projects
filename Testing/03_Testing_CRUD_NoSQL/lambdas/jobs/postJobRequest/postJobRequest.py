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

BUCKET_NAME = "crud-nosql-app-images"

table = dynamodb.Table("crud-nosql-app-maintenance-request-table")
locations_table = dynamodb.Table("crud-nosql-app-locations-table")

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Credentials": "true"
}

# $ Valid reasons for a missing/unreadable asset barcode.
# $ Kept in sync with the frontend's assetIssueReason enum.
VALID_ASSET_ISSUE_REASONS = {
    "no barcode visible",
    "barcode damaged",
    "rental unit",
    "other",
}

# $ Module-level cache for locations, reused across warm Lambda
# $ invocations within the same execution environment. Avoids a
# $ DynamoDB scan on every single job-request submission, since
# $ locations change rarely. Cleared automatically whenever AWS
# $ recycles the execution environment (cold start).
_LOCATIONS_CACHE: dict[str, str] | None = None


def get_locations():
    """
    Scans the locations table for all locations and their codes.

    Returns:
        list[dict]: Raw items from the locations table, each shaped like
        {"location": "Maitland", "code": "VTR"}.
    """
    locations = []

    try:
        response = locations_table.scan(
            ProjectionExpression="#loc, #code",
            ExpressionAttributeNames={
                "#loc": "location",
                "#code": "code"
            }
        )

        locations.extend(response.get("Items", []))

        while "LastEvaluatedKey" in response:
            response = locations_table.scan(
                ProjectionExpression="#loc, #code",
                ExpressionAttributeNames={
                    "#loc": "location",
                    "#code": "code"
                },
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )

            locations.extend(response.get("Items", []))

    except Exception as e:
        print(f"Error fetching locations: {str(e)}")

    return locations


def get_location_code_map(force_refresh: bool = False) -> dict[str, str]:
    """
    Returns a {location_name: code} lookup, backed by `_LOCATIONS_CACHE`.

    Args:
        force_refresh: Bypass the cache and re-scan the locations table.
            Not used in the request path today, but exposed in case a
            future admin endpoint needs to invalidate the cache after
            a location is added/renamed.

    Returns:
        dict[str, str]: Mapping of location name to its short code.
        Returns an empty dict if the scan fails, so callers should
        treat "location not found in map" as valid-but-uncoded rather
        than crash the request.
    """
    global _LOCATIONS_CACHE

    if _LOCATIONS_CACHE is None or force_refresh:
        items = get_locations()
        _LOCATIONS_CACHE = {
            normalize_string(item["location"]): item.get("code", "")
            for item in items
            if item.get("location")
        }

    return _LOCATIONS_CACHE


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


def generate_test_event(event: dict) -> str:
    """
    Serialises a Lambda event into a compact JSON string suitable for reuse as a test fixture.

    This function converts the incoming event dictionary into a single-line JSON string
    without extra whitespace, making it easy to copy from logs (e.g. CloudWatch) and
    reuse directly in event.json files or API Gateway test payloads.

    Args:
        event (dict): The Lambda event object received from API Gateway or another source.

    Returns:
        str: A compact JSON string representation of the event, formatted for test reuse.

    Use:
    The output of this function can be printed in the Lambda logs to capture the exact event structure for testing.
    For example, you can run this function in your Lambda handler to print the event:

    print("COPY_EVENT:", generate_test_event(event))
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "ok"})
    }
    """
    return json.dumps(event, separators=(",", ":"))


def normalize_string(value: str | None) -> str:
    return str(value or "").strip().lower()


def validate_and_build_assets(assets: object) -> list[dict]:
    """Validate and normalize every asset in a job request."""
    if not isinstance(assets, list) or not assets:
        raise ValueError("At least one asset is required")

    processed_assets = []
    seen_asset_ids = set()

    for asset_index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            raise ValueError(f"Asset {asset_index} must be a JSON object")

        for field in ("area", "equipment"):
            if not str(asset.get(field) or "").strip():
                raise ValueError(
                    f"Missing or empty field for asset {asset_index}: {field}"
                )

        asset_id = str(asset.get("assetID") or "").strip()
        issue_reason = normalize_string(asset.get("assetIssueReason"))
        issue_details = str(asset.get("assetIssueDetails") or "").strip()
        images = asset.get("images", [])

        if not isinstance(images, list):
            raise ValueError(f"Images for asset {asset_index} must be a list")
        for file_info in images:
            if not isinstance(file_info, dict):
                raise ValueError(
                    f"Every image for asset {asset_index} must be a JSON object"
                )
            filename = str(file_info.get("filename") or "").strip()
            content_type = str(file_info.get("content_type") or "").strip()
            if not filename or "/" in filename or "\\" in filename:
                raise ValueError(
                    f"Invalid image filename for asset {asset_index}"
                )
            if not content_type:
                raise ValueError(
                    f"Missing image content_type for asset {asset_index}"
                )
        if not asset_id and not issue_reason:
            raise ValueError(
                f"Either assetID or assetIssueReason is required for asset {asset_index}"
            )
        if issue_reason and issue_reason not in VALID_ASSET_ISSUE_REASONS:
            raise ValueError(
                f"Invalid assetIssueReason for asset {asset_index}: {issue_reason}"
            )
        if issue_reason == "other" and not issue_details:
            raise ValueError(
                "assetIssueDetails is required when assetIssueReason is 'other' "
                f"for asset {asset_index}"
            )
        if not asset_id and not images:
            raise ValueError(
                f"Images are compulsory if no barcode is supplied for asset {asset_index}"
            )

        if asset_id:
            duplicate_key = asset_id.casefold()
            if duplicate_key in seen_asset_ids:
                raise ValueError(f"Duplicate assetID: {asset_id}")
            seen_asset_ids.add(duplicate_key)

        processed_asset = {
            "assetIndex": asset_index,
            "area": normalize_string(asset.get("area")),
            "equipment": asset["equipment"],
            "assetIssueReason": issue_reason,
            "assetIssueDetails": issue_details,
            "images": [],
        }
        if asset_id:
            processed_asset["assetID"] = asset_id
        processed_assets.append(processed_asset)

    return processed_assets


def build_job_item(data: dict, meta: dict, assets: list[dict]) -> dict:
    """Build the DynamoDB item for one job containing multiple assets."""
    item = {
        **meta,
        "location": normalize_string(data.get("location")),
        "type": data["type"],
        "priority": normalize_string(data.get("priority")),
        "breakdown_time": data["breakdown_time"],
        "impact": data["impact"],
        "jobComments": data.get("jobComments", ""),
        "description": data["description"],
        "assets": assets,
    }

    return {k: v for k, v in item.items() if v != ""}


def lambda_handler(event, context):
    print("event:", json.dumps(event))

    try:
        if not event.get("body"):
            return _response(400, {"message": "Missing request body"})

        # $ Get the user information from the authoriser token.
        data = json.loads(event["body"])
        claims = event.get("requestContext", {}).get(
            "authorizer", {}).get("claims", {})

        # $ Validate job-level and asset-level fields.
        required_fields = ["location", "type", "priority", "impact",
                           "jobComments", "description", "breakdown_time", "assets"]
        for field in required_fields:
            if field not in data:
                return _response(400, {"message": f"Missing field: {field}"})

        try:
            processed_assets = validate_and_build_assets(data["assets"])
        except ValueError as exc:
            return _response(400, {"message": str(exc)})

        # $ Validate the submitted location against DynamoDB rather
        # $ than a hardcoded list, so newly added stores work without
        # $ a code change/deploy.
        location_codes = get_location_code_map()
        submitted_location = normalize_string(data.get("location", ""))

        if location_codes and submitted_location not in location_codes:
            return _response(400, {
                "message": f"Unknown location: {submitted_location}"
            })

        # Get the current time for the update
        sast = timezone(timedelta(hours=2))
        now = datetime.now(sast).isoformat()

        # $ Create backend meta data
        item_id = str(uuid.uuid4())
        created_at = now
        status = str("pending")

        # $ data from the cognito user sign-in
        user_id = claims.get("sub")
        user_name = claims.get("name", "")
        requested_by = f'{claims.get("name", "")} {claims.get("family_name", "")}'
        user_email = claims.get("email")

        # $ Build the jobcardNumber
        # jobcardNumber = generateJobCardNo(location_code)

        presigned_urls = []

        # $ Check if frontend included any files
        for asset_index, asset in enumerate(data["assets"]):
            for file_info in asset.get("images", []):
                filename = str(file_info["filename"]).strip()
                content_type = str(file_info["content_type"]).strip()

                # $ Generate presigned URLs for this asset's images.
                key = (
                    f"maintenance/{item_id}/assets/{asset_index}/"
                    f"images/{filename}"
                )
                url = s3.generate_presigned_url(
                    "put_object",
                    Params={
                        "Bucket": BUCKET_NAME,
                        "Key": key,
                        "ContentType": content_type
                    },
                    ExpiresIn=3600  # 1 hour
                )

                if "s3.af-south-1.amazonaws.com" not in url:
                    raise Exception(
                        "Presigned URL generated with incorrect S3 endpoint")

                upload = {
                    "type": "images",
                    "assetIndex": asset_index,
                    "filename": filename,
                    "url": url,
                    "key": key,
                    "content_type": content_type,
                }
                asset_id = str(asset.get("assetID") or "").strip()
                if asset_id:
                    upload["assetID"] = asset_id
                presigned_urls.append(upload)

        # $ Backend-generated metadata, merged with request data by
        # $ build_job_item.
        meta = {
            "id": item_id,
            "jobCreated": created_at,
            "status": normalize_string(status),
            "requested_by": normalize_string(requested_by),
            "request_sub": user_id,
            "user_email": user_email,
            "user_name": normalize_string(user_name),
        }

        item = build_job_item(data, meta, processed_assets)
        print("item:", json.dumps(item))

        table.put_item(Item=item)

        return _response(200, {"data": item, "presigned_urls": presigned_urls})

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
