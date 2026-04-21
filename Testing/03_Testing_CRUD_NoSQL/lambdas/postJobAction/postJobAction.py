import json
import boto3
import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from botocore.config import Config
from boto3.dynamodb.conditions import Key

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

TABLE_NAME = "crud-nosql-app-maintenance-action-table"
TABLE_NAME_REQUESTS = "crud-nosql-app-maintenance-request-table"
BUCKET_NAME = "crud-nosql-app-images"

table = dynamodb.Table(TABLE_NAME)
table_requests = dynamodb.Table(TABLE_NAME_REQUESTS)

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "POST,PUT,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With",
    "Access-Control-Allow-Credentials": "true"
}

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

# $ Function to get the location and requested_by from requests table
def get_request_fields_by_id(table, request_id: str) -> dict:
    """
    Get request fields by partition key id.
    Assumes table PK is 'id' and SK is 'jobCreated'.
    Returns {} if not found.
    """
    res = table.query(
        KeyConditionExpression=Key("id").eq(request_id),
        ProjectionExpression="id, jobCreated, #loc, #rb, #job",
        ExpressionAttributeNames={
            "#loc": "location",
            "#rb": "requested_by",
            "#job": "jobcardNumber",
        },
        Limit=1
    )

    items = res.get("Items", [])
    if not items:
        return {}

    item = items[0]
    return {
        "id": item.get("id"),
        "jobCreated": item.get("jobCreated"),
        "location": item.get("location"),
        "requested_by": item.get("requested_by"),
        "jobcardNumber": item.get("jobcardNumber"),
    }

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

def lambda_handler(event, context):
    # Run to capture a event.json to test the function code
    # print("COPY_EVENT:", generate_test_event(event))

    # return {
    #     "statusCode": 200,
    #     "body": json.dumps({"message": "ok"})
    # }

    method, HEADERS = handle_request_metadata(event)

    options_response = handle_options_request(method, HEADERS)
    if options_response:
        return options_response

    try:
        if not event.get("body"):
            return _response(400, {"message": "Missing request body"}, HEADERS)

        data = json.loads(event["body"])
        claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {}) # Get the user information from the authoriser token.

        # Validate required fields
        required_fields = ["start_time", "end_time", "total_km", "work_order_number", "work_completed", "status", "root_cause", "findings","signature", "selectedRowId","signedBy"]
        for field in required_fields:
            if field not in data:
                return _response(400, {"message": f"Missing field: {field}"}, HEADERS)

        # $ Create backend meta data
        item_id = str(uuid.uuid4())

        SAST = timezone(timedelta(hours=2))
        created_at = datetime.now(timezone.utc).astimezone(SAST).isoformat()

        # $ Get the location and requested_by from the requests-table
        request_id = data['selectedRowId']
        # print('request_id:', request_id)
        request_info = get_request_fields_by_id(table_requests, request_id)
        if not request_info:
            return _response(404, {"message": "Request not found"}, HEADERS)

        location = normalize_string(request_info.get("location"))
        requested_by = normalize_string(request_info.get("requested_by"))
        jobcardNumber = request_info.get("jobcardNumber", "")
        job_created = request_info.get("jobCreated")
        
        # data from the cognito user sign-in
        user_id = claims.get("sub")
        actioned_by = normalize_string(f'{claims.get("name", "")} {claims.get("family_name", "")}')

        # Check if the request was completed, if yes add a completed date.
        if data.get("status", "") == "complete":
            completed_at = datetime.now(timezone.utc).isoformat()
        else:
            completed_at = ""

        presigned_urls = []

        # Check if frontend included any files
        for file_info in data.get("images", []):
            filename = file_info.get("filename")
            content_type = file_info.get("content_type", "application/octet-stream")
            if not filename:
                continue

        # Generate presigned urls
            key = f"maintenance_action/{item_id}/{filename}"
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
                raise Exception("Presigned URL generated with incorrect S3 endpoint")

            presigned_urls.append({"filename": filename, "url": url, "key": key, "content_type": content_type})

        # Save metadata to DynamoDB
        item = {
            "id": item_id, #$ created on backend
            "actionCreated": created_at, #$ created on backend
            "request_id": data["selectedRowId"], #$ created on backend
            "action_sub": user_id,  #$ created on backend
            "actioned_by": actioned_by, #$ created on backend
            "completed_at": completed_at, #$ created on backend
            "requested_by": requested_by,#% from requests-table
            "location": location,#% from requests-table
            "jobcardNumber": jobcardNumber, #% from requests-table
            "start_time": data["start_time"],
            "end_time": data["end_time"],
            "total_km": data["total_km"],
            "work_order_number": data["work_order_number"],
            "status": normalize_string(data.get("status")),
            "root_cause": data["root_cause"],
            "work_completed": data["work_completed"],
            "findings": data["findings"],
            "images": data["images"],
            "signedBy":normalize_string(data.get("signedBy")),
            "signature": data["signature"]  # Will be updated by S3-triggered Lambda later
        }

        # $ Upddate the status of the request created status
        table_requests.update_item(
            Key={"id": data["selectedRowId"], 
                "jobCreated": job_created},
            UpdateExpression="SET #s = :status, action_id = :action_id",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":status": data["status"],
                ":action_id": item_id # $ id passed to the request table to link the 'request made & action taken'
            },
            ConditionExpression="attribute_exists(id) AND attribute_exists(jobCreated)"
        )

        table.put_item(Item=item)

        return _response(200, {"data": item, "presigned_urls": presigned_urls}, HEADERS)

    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": "Internal server error"})


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

# Run the lambda locally with the events.json file to test
if __name__ == "__main__":
    with open("event.json") as f:
        event = json.load(f)

    result = lambda_handler(event, None)
    print(json.dumps(result, indent=2))