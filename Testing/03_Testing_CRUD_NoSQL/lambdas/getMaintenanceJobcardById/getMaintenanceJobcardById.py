import json
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime
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
BUCKET = "crud-nosql-app-images"
table = dynamodb.Table(TABLE_NAME)

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With",
    "Access-Control-Allow-Credentials": "true"
}

# Change the date format in the database to readible for humans
def to_human_date(iso_string: str) -> str:
    dt = datetime.fromisoformat(iso_string)
    return dt.strftime("%d %b %Y, %H:%M")
    
def lambda_handler(event, context):
    try:
        item_id = (event.get("pathParameters") or {}).get("id")
        if not item_id:
            return _response(400, {"message": "Missing request id"})
        
        # Get the jobcard number and set to fileName
        # Use GetItem (fast, exact match)
        result = table.get_item(
            Key={"id": item_id}
        )

        item = result.get("Item")

        if not item:
            print("Jobcard not found")
            jobcardNumber = ""
        else:
            jobcardNumber = item.get("jobcardNumber", "")
            # print('jobcardNumber:', jobcardNumber)

        # Key to get file from s3 bucket
        key = f"jobcards/{item_id}.pdf"
        # Optional: force "download" and set a friendly filename
        url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": BUCKET,
                "Key": key,
                "ResponseContentType": "application/pdf",
                "ResponseContentDisposition": f'attachment; filename="{jobcardNumber}.pdf"',
            },
            ExpiresIn=600,  # 10 minutes
        )

        return _response(200, {"jobcard_url": url})

    except s3.exceptions.NoSuchKey:
        return _response(404, {"message": "PDF not found"})
    
    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": "Internal server error"})

def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": HEADERS,
        "body": json.dumps(body),
    }

if __name__ == "__main__":
    with open("event.json", "r") as f:
        event = json.load(f)

    result = lambda_handler(event, None)
    print(json.dumps(result, indent=2))