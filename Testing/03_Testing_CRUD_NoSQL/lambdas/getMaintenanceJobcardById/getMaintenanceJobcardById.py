import json
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime
from botocore.config import Config
from botocore.exceptions import ClientError

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


def to_human_date(iso_string: str) -> str:
    """
    Convert an ISO 8601 datetime string into a human-readable format.

    Args:
        iso_string: Datetime string in ISO 8601 format.

    Returns:
        A formatted datetime string in the form 'DD Mon YYYY, HH:MM'.
    """
    dt = datetime.fromisoformat(iso_string)
    return dt.strftime("%d %b %Y, %H:%M")


def get_request_by_action_id(action_id: str) -> dict | None:
    """
    Find a maintenance request record by querying the ActionIdIndex GSI.

    Args:
        action_id: The action identifier received from the frontend.

    Returns:
        The matched DynamoDB item as a dictionary, or None if not found.
    """
    response = table.query(
        IndexName="ActionIdIndex",
        KeyConditionExpression=Key("action_id").eq(action_id)
    )
    items = response.get("Items", [])
    return items[0] if items else None


def lambda_handler(event, context):
    """
    Handle the Lambda request to generate a presigned S3 URL for a jobcard PDF.

    This function:
    1. Reads the action id from the API Gateway path parameters.
    2. Queries the ActionIdIndex GSI to find the matching maintenance request.
    3. Extracts the request id and jobcard number from the matched item.
    4. Builds the S3 object key using the request id.
    5. Verifies the PDF exists in S3.
    6. Generates a presigned download URL for the PDF.
    7. Returns the URL in a JSON response.

    Args:
        event: AWS Lambda event object containing request details.
        context: AWS Lambda context object provided at runtime.

    Returns:
        A dictionary representing the HTTP response expected by API Gateway.
        - 200 if the URL is generated successfully
        - 400 if the action id is missing
        - 404 if the request or PDF is not found
        - 500 for any unexpected internal error
    """
    try:
        action_id = (event.get("pathParameters") or {}).get("id")
        if not action_id:
            return _response(400, {"message": "Missing action id"})

        item = get_request_by_action_id(action_id)
        if not item:
            return _response(404, {"message": "No request found for the provided action id"})

        request_id = item.get("id")
        if not request_id:
            return _response(404, {"message": "Request id not found on matched item"})

        jobcardNumber = item.get("jobcardNumber", "jobcard")
        key = f"jobcards/{request_id}.pdf"

        # Verify the file exists before generating the URL
        s3.head_object(Bucket=BUCKET, Key=key)

        url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": BUCKET,
                "Key": key,
                "ResponseContentType": "application/pdf",
                "ResponseContentDisposition": f'attachment; filename="{jobcardNumber}.pdf"',
            },
            ExpiresIn=600,
        )

        return _response(200, {"jobcard_url": url})

    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code in ("404", "NoSuchKey", "NotFound"):
            return _response(404, {"message": "PDF not found"})
        print("ClientError:", exc)
        return _response(500, {"message": "Internal server error"})

    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": "Internal server error"})


def _response(status_code, body):
    """
    Build a standard HTTP response for API Gateway.

    Args:
        status_code: HTTP status code to return.
        body: Response payload to be JSON-serialized.

    Returns:
        A dictionary containing the status code, headers, and JSON body.
    """
    return {
        "statusCode": status_code,
        "headers": HEADERS,
        "body": json.dumps(body),
    }