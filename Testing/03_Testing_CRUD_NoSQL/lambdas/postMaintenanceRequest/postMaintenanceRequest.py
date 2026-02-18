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
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST,PUT,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With"
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

def generateJobCardNo(location:str) -> str:
    locationID = locations.get(location)
    utc_now = datetime.now(timezone.utc)
    capeTownTime = str(utc_now + timedelta(hours=2))
    jobDate = datetime.fromisoformat(capeTownTime).strftime("%Y%m")
    count = 12
    counter = count + 1
    formattedCount=f"{counter:04d}"
    jobcardNumber=f"job-{locationID}-{jobDate}-{formattedCount}"
    return jobcardNumber

def lambda_handler(event, context):
    try:
        if not event.get("body"):
            return _response(400, {"message": "Missing request body"})
        
        data = json.loads(event["body"])
        claims = event["requestContext"]["authorizer"]["jwt"]["claims"] # Get the user information from the authoriser token.

        # Validate required fields
        required_fields = ["location", "type", "priority", "equipment", "impact", "jobComments", "description", "area", "assetID"]
        for field in required_fields:
            if field not in data:
                return _response(400, {"message": f"Missing field: {field}"})

        # Create backend meta data
        item_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        status=str("Pending")

        # data from the cognito user sign-in
        user_id = claims["sub"]
        requested_by = f'{claims.get("name", "")} {claims.get("family_name", "")}'
        
        # Build the jobcardNumber
        location = data["location"]
        jobcardNumber = generateJobCardNo(location)

        presigned_urls = []

        # Check if frontend included any files
        for file_info in data.get("images", []):
            filename = file_info.get("filename")
            content_type = file_info.get("content_type", "application/octet-stream")
            if not filename:
                continue

        # Generate presigned urls
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
            "status": status, #$ created on backend
            "requested_by": requested_by, #$ created on backend
            "jobcardNumber" : jobcardNumber, #$ created on backend
            "request_sub" : user_id, #$ created on backend
            "location": data["location"],
            "type": data["type"],
            "priority": data["priority"],
            "equipment": data["equipment"],
            "impact": data["impact"],
            "jobComments": data["jobComments"],
            "description":data["description"],
            "area":data["area"],
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
# if __name__ == "__main__":
#     with open("event.json") as f:
#         event = json.load(f)

#     result = lambda_handler(event, None)
#     print(json.dumps(result, indent=2))
