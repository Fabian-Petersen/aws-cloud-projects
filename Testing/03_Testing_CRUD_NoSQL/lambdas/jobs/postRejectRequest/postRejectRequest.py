import json
import boto3
from datetime import datetime, timezone
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

TABLE_NAME_REQUESTS = "crud-nosql-app-maintenance-request-table"
table_requests = dynamodb.Table(TABLE_NAME_REQUESTS)


def get_request_by_id(request_id: str) -> dict | None:
    """
    Retrieve a maintenance request from DynamoDB by its request ID. 
    This function queries the maintenance request table using the `id`
    partition key and returns the first matching item.  
    Args:
        request_id: The unique identifier of the request.   
    Returns:
        A dictionary representing the request item if found, otherwise `None`.  
    Notes:
        This function assumes:
        - `id` is the partition key of the table.
        - the query will return at most one logical request for the given ID.
    """
    response = table_requests.query(
        KeyConditionExpression=Key("id").eq(request_id),
        Limit=1
    )
    items = response.get("Items", [])
    return items[0] if items else None


def delete_request_images(images: list) -> list[str]:
    """
    Delete request images from S3.

    Expected image shape:
        [
            {"bucket": "bucket-name", "key": "maintenance/item_id/file.webp"},
            ...
        ]

    Args:
        images: List of image dictionaries stored on the request item.

    Returns:
        A list of S3 object keys that were successfully submitted for deletion.
    """
    deleted_keys = []

    if not isinstance(images, list):
        return deleted_keys

    for image in images:
        if not isinstance(image, dict):
            continue

        bucket = image.get("bucket")
        key = image.get("key")

        if not bucket or not key:
            continue

        s3.delete_object(Bucket=bucket, Key=key)
        deleted_keys.append(key)

    return deleted_keys


def lambda_handler(event, context):

    """
    Handle a POST request to update the status of a maintenance request.

    This Lambda function:
    - Resolves the request origin and applies CORS headers for allowed origins.
    - Handles CORS preflight OPTIONS requests.
    - Validates the incoming JSON request body.
    - Reads the target maintenance request from DynamoDB to obtain its sort key (`jobCreated`).
    - Updates the request status and message.
    - If the new status is `Rejected`, deletes the request item from DynamoDB first,
      then deletes linked request images from S3.

    Expected request body:
        {
            "selectedRowId": "<request id>",
            "status": "<new status>",
            "reject_message": "<message>"
        }

    Expected authorizer claims:
    - name
    - family_name
    - sub

    Args:
        event (dict): AWS Lambda event payload from API Gateway.
        context (LambdaContext): AWS Lambda runtime context.

    Returns:
        dict: API Gateway compatible HTTP response containing status code,
        headers, and JSON body.
    """

    #Grab the Origin header from the incoming request
    headers = event.get("headers") or {}
    origin = headers.get("origin") or headers.get("Origin") or ""
    
    allowedOrigins = [
        'https://www.crud-nosql.app.fabian-portfolio.net',
        'https://crud-nosql.app.fabian-portfolio.net',
        'http://localhost:5173'
        ]

    # Only allow known origins
    allowedOrigin = origin if origin in allowedOrigins else ""

    HEADERS = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": allowedOrigin,
        "Access-Control-Allow-Methods": "POST,OPTIONS,PUT",
        "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With",
        "Access-Control-Allow-Credentials": "true"
    }

    method = (
        event.get("httpMethod")
        or event.get("requestContext", {}).get("http", {}).get("method")
        )

    if method == "OPTIONS":
        return _response(200, {"message": "Success"}, HEADERS)

    try:
        if not event.get("body"):
            return _response(400, {"message": "Missing request body"}, HEADERS)

        data = json.loads(event["body"])
        claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})

        required_fields = ["reject_message", "status", "selectedRowId"]
        for field in required_fields:
            if field not in data or data[field] == "":
                return _response(400, {"message": f"Missing field: {field}"}, HEADERS)

        request_id = data["selectedRowId"]
        status = data["status"]
        reject_message = data["reject_message"]

        rejected_at = None
        rejected_by = None
        rejected_by_sub = None

        # Get existing item first so we can read the sort key
        existing_item = get_request_by_id(request_id)
        if not existing_item:
            return _response(404, {"message": "Request not found"}, HEADERS)
        
        # Get the SK "job_created"
        job_created = existing_item.get("jobCreated")
        if not job_created:
            return _response(500, {"message": "Existing item missing jobCreated"}, HEADERS)

        if status == "Rejected":
            rejected_at = datetime.now(timezone.utc).isoformat()
            rejected_by = f'{claims.get("name", "").strip()} {claims.get("family_name", "").strip()}'.strip()
            rejected_by_sub = claims.get("sub", "")

            table_requests.delete_item(
                Key={
                    "id": request_id,
                    "jobCreated": job_created
                },
                ConditionExpression="attribute_exists(id) AND attribute_exists(jobCreated)"
            )

            images = existing_item.get("images", [])
            deleted_keys = delete_request_images(images)

            return _response(200, {
                "message": "Request rejected and deleted successfully",
                "rejectedAt": rejected_at,
                "rejected_by": rejected_by,
                "rejected_by_sub": rejected_by_sub,
                "deletedImages": deleted_keys,
                "data": existing_item
            }, HEADERS)

        update_expression = "SET #s = :status, #m = :reject_message"
        expression_attribute_names = {
            "#s": "status",
            "#m": "reject_message",
        }
        expression_attribute_values = {
            ":status": status,
            ":reject_message": reject_message,
        }

        response = table_requests.update_item(
            Key={
                "id": request_id, 
                "jobCreated": job_created
                },
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ConditionExpression="attribute_exists(id) AND attribute_exists(jobCreated)",
            ReturnValues="ALL_NEW"
        )

        return _response(200, {
            "message": "Request updated successfully",
            "data": response.get("Attributes", {})
        }, HEADERS)

    except ClientError as exc:
        error_code = exc.response["Error"]["Code"]

        if error_code == "ConditionalCheckFailedException":
            return _response(404, {"message": "Request not found"}, HEADERS)

        print("DynamoDB Error:", exc)
        return _response(500, {"message": "Database error"}, HEADERS)

    except Exception as exc:
        print("Error:", exc)
        return _response(500, {"message": "Internal server error"}, HEADERS)

def _response(status_code, body, headers):
    """
    Build a standard API Gateway Lambda proxy response.

    Args:
        status_code (int): HTTP status code.
        body (dict): Response payload to serialize as JSON.
        headers (dict): HTTP response headers.

    Returns:
        dict: API Gateway compatible response object.
    """
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body),
    }

if __name__ == "__main__":
    with open("event.json") as f:
        event = json.load(f)

    result = lambda_handler(event, None)
    print(json.dumps(result, indent=2))



# import json
# import boto3
# from datetime import datetime, timezone
# from botocore.exceptions import ClientError
# from boto3.dynamodb.conditions import Key

# dynamodb = boto3.resource("dynamodb")

# TABLE_NAME_REQUESTS = "crud-nosql-app-maintenance-request-table"
# table_requests = dynamodb.Table(TABLE_NAME_REQUESTS)


# def get_request_by_id(request_id: str) -> dict | None:
#     """
#     Retrieve a maintenance request from DynamoDB by its request ID. 
#     This function queries the maintenance request table using the `id`
#     partition key and returns the first matching item.  
#     Args:
#         request_id: The unique identifier of the request.   
#     Returns:
#         A dictionary representing the request item if found, otherwise `None`.  
#     Notes:
#         This function assumes:
#         - `id` is the partition key of the table.
#         - the query will return at most one logical request for the given ID.
#     """
#     response = table_requests.query(
#         KeyConditionExpression=Key("id").eq(request_id),
#         Limit=1
#     )
#     items = response.get("Items", [])
#     return items[0] if items else None

# def lambda_handler(event, context):

#     """
#     Handle a POST request to update the status of a maintenance request.

#     This Lambda function:
#     - Resolves the request origin and applies CORS headers for allowed origins.
#     - Handles CORS preflight OPTIONS requests.
#     - Validates the incoming JSON request body.
#     - Reads the target maintenance request from DynamoDB to obtain its sort key (`jobCreated`).
#     - Updates the request status and message.
#     - If the new status is `Rejected`, also stores rejection metadata such as
#     timestamp, rejecting user's name, and rejecting user's Cognito subject.

#     Expected request body:
#         {
#             "selectedRowId": "<request id>",
#             "status": "<new status>",
#             "reject_message": "<message>"
#         }

#     Expected authorizer claims:
#     - name
#     - family_name
#     - sub

#     Args:
#         event (dict): AWS Lambda event payload from API Gateway.
#         context (LambdaContext): AWS Lambda runtime context.

#     Returns:
#         dict: API Gateway compatible HTTP response containing status code,
#         headers, and JSON body.
#     """

#     #Grab the Origin header from the incoming request
#     headers = event.get("headers") or {}
#     origin = headers.get("origin") or headers.get("Origin") or ""
    
#     allowedOrigins = [
#         'https://www.crud-nosql.app.fabian-portfolio.net',
#         'https://crud-nosql.app.fabian-portfolio.net',
#         'http://localhost:5173'
#         ]

#     # Only allow known origins
#     allowedOrigin = origin if origin in allowedOrigins else ""

#     HEADERS = {
#         "Content-Type": "application/json",
#         "Access-Control-Allow-Origin": allowedOrigin,
#         "Access-Control-Allow-Methods": "POST,OPTIONS,PUT",
#         "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With",
#         "Access-Control-Allow-Credentials": "true"
#     }

#     method = (
#         event.get("httpMethod")
#         or event.get("requestContext", {}).get("http", {}).get("method")
#         )

#     if method == "OPTIONS":
#         return _response(200, {"message": "Success"}, HEADERS)

#     try:
#         if not event.get("body"):
#             return _response(400, {"message": "Missing request body"}, HEADERS)

#         data = json.loads(event["body"])
#         claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})

#         required_fields = ["reject_message", "status", "selectedRowId"]
#         for field in required_fields:
#             if field not in data or data[field] == "":
#                 return _response(400, {"message": f"Missing field: {field}"}, HEADERS)

#         request_id = data["selectedRowId"]
#         status = data["status"]
#         reject_message = data["reject_message"]

#         rejected_at = None
#         rejected_by = None
#         rejected_by_sub = None

#         # Get existing item first so we can read the sort key
#         existing_item = get_request_by_id(request_id)
#         if not existing_item:
#             return _response(404, {"message": "Request not found"}, HEADERS)
        
#         # Get the SK "job_created"
#         job_created = existing_item.get("jobCreated")
#         if not job_created:
#             return _response(500, {"message": "Existing item missing jobCreated"}, HEADERS)

#         if status == "Rejected":
#             rejected_at = datetime.now(timezone.utc).isoformat()
#             rejected_by = f'{claims.get("name", "").strip()} {claims.get("family_name", "").strip()}'.strip()
#             rejected_by_sub = claims.get("sub", "")

#         update_expression = "SET #s = :status, #m = :reject_message"
#         expression_attribute_names = {
#             "#s": "status",
#             "#m": "reject_message",
#         }
#         expression_attribute_values = {
#             ":status": status,
#             ":reject_message": reject_message,
#         }

#         if status == "Rejected":
#             update_expression += ", rejectedAt = :rejected_at, rejected_by = :rejected_by, rejected_by_sub = :rejected_by_sub"
#             expression_attribute_values[":rejected_at"] = rejected_at
#             expression_attribute_values[":rejected_by"] = rejected_by
#             expression_attribute_values[":rejected_by_sub"] = rejected_by_sub

#         response = table_requests.update_item(
#             Key={
#                 "id": request_id, 
#                 "jobCreated": job_created
#                 },
#             UpdateExpression=update_expression,
#             ExpressionAttributeNames=expression_attribute_names,
#             ExpressionAttributeValues=expression_attribute_values,
#             ConditionExpression="attribute_exists(id) AND attribute_exists(jobCreated)",
#             ReturnValues="ALL_NEW"
#         )

#         return _response(200, {
#             "message": "Request updated successfully",
#             "data": response.get("Attributes", {})
#         }, HEADERS)

#     except ClientError as exc:
#         error_code = exc.response["Error"]["Code"]

#         if error_code == "ConditionalCheckFailedException":
#             return _response(404, {"message": "Request not found"}, HEADERS)

#         print("DynamoDB Error:", exc)
#         return _response(500, {"message": "Database error"}, HEADERS)

#     except Exception as exc:
#         print("Error:", exc)
#         return _response(500, {"message": "Internal server error"}, HEADERS)

# def _response(status_code, body, headers):
#     """
#     Build a standard API Gateway Lambda proxy response.

#     Args:
#         status_code (int): HTTP status code.
#         body (dict): Response payload to serialize as JSON.
#         headers (dict): HTTP response headers.

#     Returns:
#         dict: API Gateway compatible response object.
#     """
#     return {
#         "statusCode": status_code,
#         "headers": headers,
#         "body": json.dumps(body),
#     }

# if __name__ == "__main__":
#     with open("event.json") as f:
#         event = json.load(f)

#     result = lambda_handler(event, None)
#     print(json.dumps(result, indent=2))