import json
import boto3
from datetime import datetime, timezone
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

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

def get_request_by_id(request_id: str):
    response = table_requests.query(
        KeyConditionExpression=Key("id").eq(request_id),
        Limit=1
    )
    items = response.get("Items", [])
    return items[0] if items else None

def lambda_handler(event, context):
    try:
        if not event.get("body"):
            return _response(400, {"message": "Missing request body"})

        data = json.loads(event["body"])
        claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})

        required_fields = [
            "targetDate",
            "status",
            "selectedRowId",
            "assign_to_name",
            "assign_to_sub",
            "assign_to_group"
        ]
        for field in required_fields:
            if field not in data or data[field] == "":
                return _response(400, {"message": f"Missing field: {field}"})

        request_id = data["selectedRowId"]
        action_status = data["status"]
        targetDate = data["targetDate"]
        assign_to_name = data["assign_to_name"]
        assign_to_sub = data["assign_to_sub"]
        assign_to_group = data["assign_to_group"]

        # Get existing item first so we can read the sort key
        existing_item = get_request_by_id(request_id)
        if not existing_item:
            return _response(404, {"message": "Request not found"})

        job_created = existing_item.get("jobCreated")
        if not job_created:
            return _response(500, {"message": "Existing item missing jobCreated"})

        # Frontend action -> DB status
        db_status = "In Progress" if action_status == "Approved" else action_status

        update_expression = """
            SET #s = :status,
                #td = :targetDate,
                #an = :assign_to_name,
                #as = :assign_to_sub,
                #ag = :assign_to_group
        """

        expression_attribute_names = {
            "#s": "status",
            "#td": "targetDate",
            "#an": "assign_to_name",
            "#as": "assign_to_sub",
            "#ag": "assign_to_group",
        }

        expression_attribute_values = {
            ":status": db_status,
            ":targetDate": targetDate,
            ":assign_to_name": assign_to_name,
            ":assign_to_sub": assign_to_sub,
            ":assign_to_group": assign_to_group,
        }

        if action_status == "Approved":
            approved_at = datetime.now(timezone.utc).isoformat()
            approved_by = f'{claims.get("name", "").strip()} {claims.get("family_name", "").strip()}'.strip()
            approved_by_sub = claims.get("sub", "")

            update_expression += ", approved_at = :approved_at, approved_by = :approved_by, approved_by_sub = :approved_by_sub"
            expression_attribute_values[":approved_at"] = approved_at
            expression_attribute_values[":approved_by"] = approved_by
            expression_attribute_values[":approved_by_sub"] = approved_by_sub

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
            "message": "Request approved",
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