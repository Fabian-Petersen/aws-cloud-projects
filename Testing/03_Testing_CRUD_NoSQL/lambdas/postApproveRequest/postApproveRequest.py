import json
import boto3
from datetime import datetime, timezone
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")

TABLE_NAME_REQUESTS = "crud-nosql-app-maintenance-request-table"
table_requests = dynamodb.Table(TABLE_NAME_REQUESTS)

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "POST,PUT,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With",
    "Access-Control-Allow-Credentials": "true"
}

def lambda_handler(event, context):
    try:
        if not event.get("body"):
            return _response(400, {"message": "Missing request body"})

        data = json.loads(event["body"])
        claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})

        required_fields = ["targetDate", "status", "selectedRowId", "assigned_to"]
        for field in required_fields:
            if field not in data or data[field] == "":
                return _response(400, {"message": f"Missing field: {field}"})

        request_id = data["selectedRowId"]
        status = data["status"]
        targetDate = data["targetDate"]
        assigned_to = data["assigned_to"]

        approved_at = None
        approved_by = None
        approved_by_sub = None

        if status == "Approved":
            approved_at = datetime.now(timezone.utc).isoformat()
            approved_by = f'{claims.get("name", "").strip()} {claims.get("family_name", "").strip()}'.strip()
            approved_by_sub = claims.get("sub", "")

        update_expression = "SET #s = :status, #m = :targetDate"
        expression_attribute_names = {
            "#s": "status",
            "#m": "targetDate",
        }
        expression_attribute_values = {
            ":status": "In Progress",
            ":targetDate": targetDate,
        }

        if status == "In Progress":
            update_expression += ", rejectedAt = :approved_at, approved_by = :approved_by, approved_by_sub = :approved_by_sub"
            expression_attribute_values[":approved_at"] = approved_at
            expression_attribute_values[":approved_by"] = approved_by
            expression_attribute_values[":approved_by_sub"] = approved_by_sub

        response = table_requests.update_item(
            Key={"id": request_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ConditionExpression="attribute_exists(id)",
            ReturnValues="ALL_NEW"
        )

        return _response(200, {
            "message": "Request Approved",
            "data": response.get("Attributes", {})
        })

    except ClientError as exc:
        error_code = exc.response["Error"]["Code"]

        if error_code == "ConditionalCheckFailedException":
            return _response(404, {"message": "Request not found"})

        print("DynamoDB Error:", exc)
        return _response(500, {"message": "Database error"})

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
    with open("event.json") as f:
        event = json.load(f)

    result = lambda_handler(event, None)
    print(json.dumps(result, indent=2))