import json
import boto3
from datetime import datetime, timezone, timedelta
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
  'Phillipi': 'PHP',
  'Bellville': 'BTX',
  'Khayelitsha': 'IKH',
  'Wynberg': 'WBG',
  'Maitland': 'VTR',
  'Golden Acre': 'GAC',
  'Distribution Centre': 'DCN',
  'Central Services': 'CTS'
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
    start_of_month = now_ct.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
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

def generate_jobcard_no(location: str) -> str:
    """
    Generate the next jobcard number for a given location.

    The jobcard number is built using the location code, the current year and
    month in YYYYMM format, and the next sequential number for that location
    within the current month.

    Format: Job-<LOCATION_CODE>-<YYYYMM>-<SEQUENCE>

    Example: Job-PHP-202603-0007

    Args:
        location: The full location name used to look up the location code and count existing jobcards for the current month.

    Returns:
        A formatted jobcard number string for the next request at the specified location.

    Raises:
        ValueError: If the provided location does not exist in the `locations` mapping.

    Notes:
        This function assumes:
        - `locations` contains a valid code for each supported location.
        - `get_monthly_jobcard_count()` returns the current number of jobcards for the given location in the current month.
        - `get_month_bounds()` returns the current month in YYYYMM format as
        its third value.
        - the generated sequence is based on the current count plus one.
    """
    location_id = locations.get(location)
    if not location_id:
        raise ValueError(f"Unknown location: {location}")

    count = get_monthly_jobcard_count(location)
    next_number = count + 1

    _, _, job_date = get_month_bounds()
    formatted_count = f"{next_number:04d}"

    return f"Job-{location_id}-{job_date}-{formatted_count}"

def lambda_handler(event, context):
    """
    Process a maintenance request approval.

    This Lambda function validates the incoming API request body, retrieves the
    existing maintenance request from DynamoDB, and updates the request with the
    provided assignment and target date details.

    When the incoming status is `Approved`, the function:
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
        
        # $ Get the location of the request to build the jobcard
        location = existing_item.get("location")
        if not location:
            return _response(500, {"message": "Location not found"})

        # Build the jobcard
        jobcardNumber = generate_jobcard_no(location)

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
            "#ag": "assign_to_group"
        }

        expression_attribute_values = {
            ":status": db_status,
            ":targetDate": targetDate,
            ":assign_to_name": assign_to_name,
            ":assign_to_sub": assign_to_sub,
            ":assign_to_group": assign_to_group
        }

        if action_status == "Approved":
            approved_at = datetime.now(timezone.utc).isoformat()
            approved_by = f'{claims.get("name", "").strip()} {claims.get("family_name", "").strip()}'.strip()
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