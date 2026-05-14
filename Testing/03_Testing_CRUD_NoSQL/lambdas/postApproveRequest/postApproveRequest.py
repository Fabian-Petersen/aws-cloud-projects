import json
import boto3
from datetime import datetime, timezone, timedelta
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")

TABLE_NAME_REQUESTS = "crud-nosql-app-maintenance-request-table"
table_requests = dynamodb.Table(TABLE_NAME_REQUESTS)

TABLE_NAME_JOBCARD_SEQUENCE = "crud-nosql-app-jobcard-sequences-table"
table_jobcard_sequence = dynamodb.Table(TABLE_NAME_JOBCARD_SEQUENCE)

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "POST,PUT,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With",
    "Access-Control-Allow-Credentials": "true"
}


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


locations = {
    'phillipi': 'PHP',
    'bellville': 'BTX',
    'khayelitsha': 'IKH',
    'wynberg': 'WBG',
    'maitland': 'VTR',
    'golden acre': 'GAC',
    'distribution centre': 'DCN',
    'central services': 'CTS'
}


def get_cape_town_now() -> datetime:
    """
    Return the current date and time in Cape Town.

    Returns:
        A timezone-aware datetime object representing the current
        date and time in Cape Town (UTC+2).
    """
    utc_now = datetime.now(timezone.utc)
    return utc_now.astimezone(timezone(timedelta(hours=2)))


def get_month_bounds():
    """
    Return the current month's date boundaries for Cape Town time.

    This function calculates the start of the current month, the start of the
    next month, and a formatted year-month string based on the current date
    and time in Cape Town.

    Returns:
        A tuple containing:
        - start_of_month: ISO 8601 string for the first moment of the current month
        - next_month: ISO 8601 string for the first moment of the next month
        - current_month_code: A string in YYYYMM format for the current month
    """
    now_ct = get_cape_town_now()
    start_of_month = now_ct.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0)
    if now_ct.month == 12:
        next_month = now_ct.replace(
            year=now_ct.year + 1,
            month=1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )
    else:
        next_month = now_ct.replace(
            month=now_ct.month + 1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

    return start_of_month.isoformat(), next_month.isoformat(), now_ct.strftime("%Y%m")


def get_monthly_jobcard_count(location: str) -> int:
    """
    Return the number of requests for a given location in the current month.

    This function queries the `LocationIndex` global secondary index in DynamoDB
    and counts all request items where the `location` matches the given value
    and the `jobCreated` date falls within the current month.

    Pagination is handled automatically so that all matching items are counted,
    even when the query result spans multiple pages.

    Args:
        location: The location name used to filter request records.

    Returns:
        The total number of request items for the specified location in the
        current month.

    Notes:
        This function assumes:
        - `LocationIndex` exists on the table.
        - `location` is the partition key of `LocationIndex`.
        - `jobCreated` is the sort key of `LocationIndex`.
        - `jobCreated` is stored in a format that supports chronological range queries, such as ISO 8601.
    """
    start_date, end_date, _ = get_month_bounds()

    total_count = 0
    last_evaluated_key = None

    while True:
        params = {
            "IndexName": "LocationIndex",
            "KeyConditionExpression": (
                Key("location").eq(location) &
                Key("jobCreated").between(start_date, end_date)
            ),
            "Select": "COUNT"
        }

        if last_evaluated_key:
            params["ExclusiveStartKey"] = last_evaluated_key

        response = table_requests.query(**params)
        total_count += response.get("Count", 0)

        last_evaluated_key = response.get("LastEvaluatedKey")
        if not last_evaluated_key:
            break

    return total_count


def generate_jobcard_no(location: str, request_id: str) -> str:
    """
    Generate the next jobcard number for a given location using an atomic
    counter stored in a separate DynamoDB table.

    The counter is partitioned by location code and month (YYYYMM), so each
    location has its own monthly sequence.

    Counter item example:
        {
            "id": "JOBCARD#PHP#202603",
            "lastSequence": 7,
            "lastRequestId": "<request_id>",
            "updatedAt": "<iso timestamp>"
        }

    Format:
        Job-<LOCATION_CODE>-<YYYYMM>-<SEQUENCE>

    Example:
        Job-PHP-202603-0008
    """
    location_id = locations.get(location)
    if not location_id:
        raise ValueError(f"Unknown location: {location}")

    _, _, job_date = get_month_bounds()
    counter_id = f"JOBCARD#{location_id}#{job_date}"
    now_iso = datetime.now(timezone.utc).isoformat()

    response = table_jobcard_sequence.update_item(
        Key={"id": counter_id},
        UpdateExpression="""
            SET lastSequence = if_not_exists(lastSequence, :zero) + :inc,
                lastRequestId = :request_id,
                updatedAt = :updated_at
        """,
        ExpressionAttributeValues={
            ":zero": 0,
            ":inc": 1,
            ":request_id": request_id,
            ":updated_at": now_iso
        },
        ReturnValues="UPDATED_NEW"
    )

    next_number = int(response["Attributes"]["lastSequence"])
    return f"Job-{location_id}-{job_date}-{next_number:04d}"


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
    """
    Process a maintenance request approval.

    This Lambda function validates the incoming API request body, retrieves the
    existing maintenance request from DynamoDB, and updates the request with the
    provided assignment and target date details.

    When the incoming status is `approved`, the function:
    - changes the stored database status to `In Progress`
    - generates a new jobcard number based on the request location
    - records approval metadata, including the approval timestamp and approver details

    For all other supported statuses, the function updates the request without
    generating approval metadata.

    Args:
        event: The AWS Lambda event payload from API Gateway. Expected to contain:
            - `body`: A JSON string with:
                - `targetDate`
                - `status`
                - `selectedRowId`
                - `assign_to_name`
                - `assign_to_sub`
                - `assign_to_group`
            - `requestContext.authorizer.claims`: Cognito user claims for the authenticated user performing the action.
        context: The AWS Lambda context runtime information. Not used directly
            in this function.

    Returns:
        A dictionary containing:
        - `statusCode`: HTTP response status code
        - `headers`: Response headers
        - `body`: JSON-encoded response message and, on success, the updated item

    Response codes:
        - 200: The request was updated successfully
        - 400: The request body or required fields are missing
        - 404: The request could not be found
        - 500: A server-side or database error occurred

    Notes:
        This function assumes:
        - the DynamoDB table uses `id` as the partition key and `jobCreated`
        as the sort key
        - `get_request_by_id()` returns the existing request item
        - `generate_jobcard_no()` returns a valid jobcard number for the
        request location
        - the frontend may send `Approved`, but the database stores this as
        `In Progress`
    """
    # print("COPY_EVENT:", generate_test_event(event))
    # return {
    #     "statusCode": 200,
    #     "body": json.dumps({"message": "ok"})
    # }

    try:
        if not event.get("body"):
            return _response(400, {"message": "Missing request body"})

        data = json.loads(event["body"])
        claims = event.get("requestContext", {}).get(
            "authorizer", {}).get("claims", {})

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
        action_status = normalize_string(data.get("status"))
        targetDate = data["targetDate"]
        assign_to_name = normalize_string(data.get("assign_to_name"))
        assign_to_sub = normalize_string(data.get("assign_to_sub"))
        assign_to_group = normalize_string(data.get("assign_to_group"))

        # Get existing item first so we can read the sort key
        existing_item = get_request_by_id(request_id)
        if not existing_item:
            return _response(404, {"message": "Request not found"})

        job_created = existing_item.get("jobCreated")
        if not job_created:
            return _response(500, {"message": "Existing item missing jobCreated"})

        # $ Get the location when we need to build the jobcard
        location = existing_item.get("location")
        if action_status == "approved" and not location:
            return _response(500, {"message": "Location not found"})

        # Frontend action -> DB status
        db_status = "in progress" if action_status == "approved" else action_status

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
            "#ag": "assign_to_group"
        }

        expression_attribute_values = {
            ":status": db_status,
            ":targetDate": targetDate,
            ":assign_to_name": assign_to_name,
            ":assign_to_sub": assign_to_sub,
            ":assign_to_group": assign_to_group
        }

        if action_status == "approved":
            jobcardNumber = generate_jobcard_no(location, request_id)
            approved_at = datetime.now(timezone.utc).isoformat()
            approved_by = f'{claims.get("name", "").strip()} {claims.get("family_name", "").strip()}'.strip(
            )
            approved_by_sub = claims.get("sub", "")

            update_expression += """,
                approved_at = :approved_at,
                approved_by = :approved_by,
                approved_by_sub = :approved_by_sub,
                jobcardNumber = :jobcardNumber
            """
            expression_attribute_values[":approved_at"] = approved_at
            expression_attribute_values[":approved_by"] = approved_by
            expression_attribute_values[":approved_by_sub"] = approved_by_sub
            expression_attribute_values[":jobcardNumber"] = jobcardNumber

            condition_expression = "attribute_exists(id) AND attribute_exists(jobCreated)"

            if action_status == "approved":
                condition_expression += " AND attribute_not_exists(jobcardNumber)"

            response = table_requests.update_item(
                Key={
                    "id": request_id,
                    "jobCreated": job_created
                },
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
                ConditionExpression=condition_expression,
                ReturnValues="ALL_NEW"
            )

        return _response(200, {
            "message": "Request updated successfully...",
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
