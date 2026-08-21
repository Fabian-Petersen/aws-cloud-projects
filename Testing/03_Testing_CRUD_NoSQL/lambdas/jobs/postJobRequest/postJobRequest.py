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
VALID_ASSET_ISSUE_REASONS = {"No barcode visible",
                             "barcode damaged", "rental unit", "", "other"}

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
            item["location"]: item.get("code", "")
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


def build_job_item(data: dict, meta: dict) -> dict:
    """
    Builds the DynamoDB item for a job request.

    Any attribute with an empty-string value is omitted entirely rather
    than written as "". This matters specifically for `assetID`, which
    is a key attribute on the AssetIdIndex GSI. DynamoDB rejects empty
    strings as index key values on a PutItem/UpdateItem call, and a
    sparse GSI is designed to simply skip items that don't carry the
    attribute at all — so omitting it is both the fix and the correct
    modelling choice for "this job has no identified asset".

    Args:
        data: The parsed request body from the frontend.
        meta: Backend-generated metadata (id, timestamps, requester info).

    Returns:
        dict: The item ready for `table.put_item(Item=...)`.
    """
    item = {
        **meta,
        "location": normalize_string(data.get("location")),
        "type": data["type"],
        "priority": normalize_string(data.get("priority")),
        "equipment": data["equipment"],
        "breakdown_time": data["breakdown_time"],
        "impact": data["impact"],
        "jobComments": data.get("jobComments", ""),
        "description": data["description"],
        "area": normalize_string(data.get("area")),
        "assetID": data.get("assetID", ""),
        "assetIssueReason": data.get("assetIssueReason", ""),
        "assetIssueDetails": data.get("assetIssueDetails", ""),
        "images": [],  # Will be updated by S3-triggered Lambda later
    }

    # Strip empty-string attributes so assetID (a GSI key) is omitted
    # entirely rather than written as "".
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

        # $ Validate required fields
        #
        # assetID is deliberately NOT in this list. A job request is
        # valid either with a verified assetID OR with an
        # assetIssueReason explaining why one isn't available — see
        # the check below.
        required_fields = ["location", "type", "priority", "equipment", "impact",
                           "jobComments", "description", "area", "breakdown_time"]
        for field in required_fields:
            if field not in data:
                return _response(400, {"message": f"Missing field: {field}"})

        # $ Validate the submitted location against DynamoDB rather
        # $ than a hardcoded list, so newly added stores work without
        # $ a code change/deploy.
        location_codes = get_location_code_map()
        submitted_location = data.get("location", "")

        if location_codes and submitted_location not in location_codes:
            return _response(400, {
                "message": f"Unknown location: {submitted_location}"
            })

        location_code = location_codes.get(submitted_location, "")

        asset_id = str(data.get("assetID") or "").strip()
        asset_issue_reason = str(data.get("assetIssueReason") or "").strip()
        asset_issue_details = str(data.get("assetIssueDetails") or "").strip()
        images = data.get("images", [])

        # $ Business rule: the job needs either a verified assetID, or
        # $ an explanation for why one couldn't be provided. Both being
        # $ empty means the frontend cascade was bypassed (or the
        # $ request was hand-crafted) — reject rather than silently
        # $ writing an unidentified job with no context.
        if not asset_id and not asset_issue_reason:
            return _response(400, {
                "message": "Either assetID or assetIssueReason is required"
            })

        if asset_issue_reason and asset_issue_reason not in VALID_ASSET_ISSUE_REASONS:
            return _response(400, {
                "message": f"Invalid assetIssueReason: {asset_issue_reason}"
            })

        # $ "other" requires a written explanation.
        if asset_issue_reason == "other" and not asset_issue_details:
            return _response(400, {
                "message": "assetIssueDetails is required when assetIssueReason is 'other'"
            })

        # $ Photographic evidence is compulsory whenever there's no
        # $ verified asset ID, regardless of which reason was given.
        if asset_issue_reason and not images:
            return _response(400, {
                "message": "Images are compulsory if no barcode is supplied"
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
        for file_info in images:
            filename = file_info.get("filename")
            content_type = file_info.get(
                "content_type", "application/octet-stream")
            if not filename:
                continue

        # $ Generate presigned urls
            key = f"maintenance/{item_id}/{filename}"
            url = s3.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": BUCKET_NAME,
                    "Key": key,
                    "ContentType": content_type
                },
                ExpiresIn=3600  # 1 hour
            )

            # The config above force the url to be af-south-1 region and the code below check if the url is region specific.
            if "s3.af-south-1.amazonaws.com" not in url:
                raise Exception(
                    "Presigned URL generated with incorrect S3 endpoint")

            presigned_urls.append(
                {"filename": filename, "url": url, "key": key, "content_type": content_type})

        # $ Backend-generated metadata, merged with request data by
        # $ build_job_item.
        meta = {
            "id": item_id,
            "jobCreated": created_at,
            "status": normalize_string(status),
            "requested_by": normalize_string(requested_by),
            # "jobcardNumber" : jobcardNumber,
            "request_sub": user_id,
            "user_email": user_email,
            "user_name": normalize_string(user_name),
        }

        item = build_job_item(data, meta)

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

# ---------------------------------------------------------------------------- #
#                                 Old Function                                 #
# ---------------------------------------------------------------------------- #


# import json
# import boto3
# import uuid
# from datetime import datetime, timezone, timedelta
# from botocore.config import Config


# dynamodb = boto3.resource("dynamodb")
# s3 = boto3.client(
#     "s3",
#     region_name="af-south-1",
#     config=Config(
#         s3={"addressing_style": "virtual"},
#         signature_version="s3v4",
#         region_name="af-south-1"
#     )
# )

# TABLE_NAME = "crud-nosql-app-maintenance-request-table"
# BUCKET_NAME = "crud-nosql-app-images"
# table = dynamodb.Table(TABLE_NAME)

# HEADERS = {
#     "Content-Type": "application/json",
#     "Access-Control-Allow-Origin": "http://localhost:5173",
#     "Access-Control-Allow-Methods": "POST,OPTIONS",
#     "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
#     "Access-Control-Allow-Credentials": "true"
# }

# locations = {
#     'Phillipi': 'PHP',
#     'Bellville': 'BTX',
#     'Khayelitsha': 'IKH',
#     'Wynberg': 'WBG',
#     'Maitland': 'VTR',
#     'Golden Acre': 'GAC',
#     'Distribution Centre': 'DCN',
#     'Central Services': 'CTS'
# }

# # $ Change the date format in the database to readible for humans


# def to_human_date(iso_string: str) -> str:
#     """
#     Convert an ISO 8601 timestamp string to a human-readable date in SAST.

#     Args:
#         iso_string (str): ISO formatted datetime string (e.g., "2024-01-01T12:00:00Z").

#     Returns:
#         str: Formatted date string (e.g., "01 Jan 2024, 14:00").
#     """
#     SAST = timezone(timedelta(hours=2))
#     dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
#     return dt.astimezone(SAST).strftime("%d %b %Y, %H:%M")


# def generate_test_event(event: dict) -> str:
#     """
#     Serialises a Lambda event into a compact JSON string suitable for reuse as a test fixture.

#     This function converts the incoming event dictionary into a single-line JSON string
#     without extra whitespace, making it easy to copy from logs (e.g. CloudWatch) and
#     reuse directly in event.json files or API Gateway test payloads.

#     Args:
#         event (dict): The Lambda event object received from API Gateway or another source.

#     Returns:
#         str: A compact JSON string representation of the event, formatted for test reuse.

#     Use:
#     The output of this function can be printed in the Lambda logs to capture the exact event structure for testing.
#     For example, you can run this function in your Lambda handler to print the event:

#     print("COPY_EVENT:", generate_test_event(event))
#     return {
#         "statusCode": 200,
#         "body": json.dumps({"message": "ok"})
#     }
#     """
#     return json.dumps(event, separators=(",", ":"))


# def normalize_string(value: str | None) -> str:
#     return str(value or "").strip().lower()


# def lambda_handler(event, context):
#     # print("COPY_EVENT:", generate_test_event(event))
#     # return {
#     #     "statusCode": 200,
#     #     "body": json.dumps({"message": "ok"})
#     # }

#     try:
#         if not event.get("body"):
#             return _response(400, {"message": "Missing request body"})

#         # $ Get the user information from the authoriser token.
#         data = json.loads(event["body"])
#         claims = event.get("requestContext", {}).get(
#             "authorizer", {}).get("claims", {})

#         # $ Validate required fields
#         required_fields = ["location", "type", "priority", "equipment", "impact",
#                            "jobComments", "description", "area", "assetID", "breakdown_time"]
#         for field in required_fields:
#             if field not in data:
#                 return _response(400, {"message": f"Missing field: {field}"})

#         # Get the current time for the update
#         sast = timezone(timedelta(hours=2))
#         now = datetime.now(sast).isoformat()

#         # $ Create backend meta data
#         item_id = str(uuid.uuid4())
#         created_at = now
#         status = str("pending")

#         # $ data from the cognito user sign-in
#         user_id = claims.get("sub")
#         user_name = claims.get("name", "")
#         requested_by = f'{claims.get("name", "")} {claims.get("family_name", "")}'
#         user_email = claims.get("email")

#         # $ Build the jobcardNumber
#         # location = data["location"]
#         # jobcardNumber = generateJobCardNo(location)

#         presigned_urls = []

#         # $ Check if frontend included any files
#         for file_info in data.get("images", []):
#             filename = file_info.get("filename")
#             content_type = file_info.get(
#                 "content_type", "application/octet-stream")
#             if not filename:
#                 continue

#         # $ Generate presigned urls
#             key = f"maintenance/{item_id}/{filename}"
#             url = s3.generate_presigned_url(
#                 "put_object",
#                 Params={
#                     "Bucket": BUCKET_NAME,
#                     "Key": key,
#                     "ContentType": content_type
#                 },
#                 ExpiresIn=3600  # 1 hour
#             )

#             # The config above force the url to be af-south-1 region and the code below check if the url is region specific.
#             if "s3.af-south-1.amazonaws.com" not in url:
#                 raise Exception(
#                     "Presigned URL generated with incorrect S3 endpoint")

#             presigned_urls.append(
#                 {"filename": filename, "url": url, "key": key, "content_type": content_type})

#         # Save metadata to DynamoDB
#         item = {
#             "id": item_id,  # $ created on backend
#             "jobCreated": created_at,  # $ created on backend
#             "status": normalize_string(status),  # $ created on backend
#             # $ created on backend for Jobcard
#             "requested_by": normalize_string(requested_by),
#             # "jobcardNumber" : jobcardNumber, #$ created on backend
#             "request_sub": user_id,  # $ created on backend
#             "user_email": user_email,  # $ created on backend
#             "user_name": normalize_string(user_name),  # $ created on backend
#             "location": normalize_string(data.get("location")),
#             "type": data["type"],
#             "priority": normalize_string(data.get("priority")),
#             "equipment": data["equipment"],
#             "breakdown_time": data["breakdown_time"],
#             "impact": data["impact"],
#             "jobComments": data["jobComments"],
#             "description": data["description"],
#             "area": normalize_string(data.get("area")),
#             "assetID": data["assetID"],
#             "images": []  # Will be updated by S3-triggered Lambda later
#         }

#         table.put_item(Item=item)

#         return _response(200, {"data": item, "presigned_urls": presigned_urls})

#     except Exception as exc:
#         print("Error:", exc)
#         return _response(500, {"message": "Internal server error"})


# def _response(status_code, body):
#     return {
#         "statusCode": status_code,
#         "headers": HEADERS,
#         "body": json.dumps(body),
#     }


# # Run the lambda locally with the events.json file to test
# if __name__ == "__main__":
#     with open("event.json") as f:
#         event = json.load(f)

#     result = lambda_handler(event, None)
#     print(json.dumps(result, indent=2))
