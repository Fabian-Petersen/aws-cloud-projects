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

TABLE_NAME = "crud-nosql-app-maintenance-request-table"
BUCKET_NAME = "crud-nosql-app-images"
table = dynamodb.Table(TABLE_NAME)

HEADERS = {
"Content-Type": "application/json",
"Access-Control-Allow-Origin": "http://localhost:5173",
"Access-Control-Allow-Methods": "POST,OPTIONS",
"Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
"Access-Control-Allow-Credentials": "true"
}

locations = {
  'Phillipi': 'PHP',
  'Bellville': 'BTX',
  'Khayelitsha': 'IKH',
  'Wynberg': 'WBG',
  'Maitland': 'VTR',
  'Golden Acre': 'GAC',
  'Distribution Centre': 'DCN',
  'Central Services': 'CTS'
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
    # print("COPY_EVENT:", generate_test_event(event))
    # return {
    #     "statusCode": 200,
    #     "body": json.dumps({"message": "ok"})
    # }

    try:
        if not event.get("body"):
            return _response(400, {"message": "Missing request body"})
        
        #$ Get the user information from the authoriser token.
        data = json.loads(event["body"])
        claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {}) 

        #$ Validate required fields
        required_fields = ["location", "type", "priority", "equipment", "impact", "jobComments", "description", "area", "assetID"]
        for field in required_fields:
            if field not in data:
                return _response(400, {"message": f"Missing field: {field}"})
            
        # Get the current time for the update
        sast = timezone(timedelta(hours=2))
        now = datetime.now(sast).isoformat()

        #$ Create backend meta data
        item_id = str(uuid.uuid4())
        created_at = now
        status=str("pending")

        #$ data from the cognito user sign-in
        user_id = claims.get("sub")
        user_name = claims.get("name","")
        requested_by = f'{claims.get("name", "")} {claims.get("family_name", "")}'
        user_email = claims.get("email")
        
        #$ Build the jobcardNumber
        # location = data["location"]
        # jobcardNumber = generateJobCardNo(location)

        presigned_urls = []

        #$ Check if frontend included any files
        for file_info in data.get("images", []):
            filename = file_info.get("filename")
            content_type = file_info.get("content_type", "application/octet-stream")
            if not filename:
                continue

        #$ Generate presigned urls
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
                raise Exception("Presigned URL generated with incorrect S3 endpoint")

            presigned_urls.append({"filename": filename, "url": url, "key": key, "content_type": content_type})

        # Save metadata to DynamoDB
        item = {
            "id": item_id, #$ created on backend
            "jobCreated": created_at, #$ created on backend
            "status": normalize_string(status), #$ created on backend
            "requested_by": normalize_string(requested_by), #$ created on backend for Jobcard
            # "jobcardNumber" : jobcardNumber, #$ created on backend
            "request_sub" : user_id, #$ created on backend
            "user_email" : user_email, #$ created on backend
            "user_name" : normalize_string(user_name), #$ created on backend
            "location": normalize_string(data.get("location")),
            "type": data["type"],
            "priority": normalize_string(data.get("priority")),
            "equipment": data["equipment"],
            "impact": data["impact"],
            "jobComments": data["jobComments"],
            "description":data["description"],
            "area":normalize_string(data.get("area")),
            "assetID":data["assetID"],
            "images": []  # Will be updated by S3-triggered Lambda later
        }

        table.put_item(Item=item)

        return _response(200, {"data":item, "presigned_urls": presigned_urls})

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