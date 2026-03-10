import json
import boto3
from datetime import datetime, timezone
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")

TABLE_NAME_REQUESTS = "crud-nosql-app-maintenance-request-table"
table_requests = dynamodb.Table(TABLE_NAME_REQUESTS)


def lambda_handler(event, context):

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
        message = data["reject_message"]

        rejected_at = None
        rejected_by = None
        rejected_by_sub = None

        if status == "Rejected":
            rejected_at = datetime.now(timezone.utc).isoformat()
            rejected_by = f'{claims.get("name", "").strip()} {claims.get("family_name", "").strip()}'.strip()
            rejected_by_sub = claims.get("sub", "")

        update_expression = "SET #s = :status, #m = :message"
        expression_attribute_names = {
            "#s": "status",
            "#m": "message",
        }
        expression_attribute_values = {
            ":status": status,
            ":message": message,
        }

        if status == "Rejected":
            update_expression += ", rejectedAt = :rejected_at, rejected_by = :rejected_by, rejected_by_sub = :rejected_by_sub"
            expression_attribute_values[":rejected_at"] = rejected_at
            expression_attribute_values[":rejected_by"] = rejected_by
            expression_attribute_values[":rejected_by_sub"] = rejected_by_sub

        response = table_requests.update_item(
            Key={"id": request_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ConditionExpression="attribute_exists(id)",
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