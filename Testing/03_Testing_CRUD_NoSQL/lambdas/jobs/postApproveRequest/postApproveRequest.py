import json
import boto3

from datetime import datetime, timezone, timedelta
from decimal import Decimal

from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key


# ---------------------------------------------------------------------------- #
#                                  AWS SETUP                                   #
# ---------------------------------------------------------------------------- #

dynamodb = boto3.resource("dynamodb")


TABLE_NAME_REQUESTS = "crud-nosql-app-maintenance-request-table"
table_requests = dynamodb.Table(TABLE_NAME_REQUESTS)


TABLE_NAME_JOBCARD_SEQUENCE = "crud-nosql-app-jobcard-sequences-table"
table_jobcard_sequence = dynamodb.Table(TABLE_NAME_JOBCARD_SEQUENCE)


TABLE_NAME_LOCATIONS = "crud-nosql-app-locations-table"
table_locations = dynamodb.Table(TABLE_NAME_LOCATIONS)


HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "POST,PUT,OPTIONS",
    "Access-Control-Allow-Headers":
        "Content-Type,Authorization,X-Amz-Date,X-Api-Key,"
        "X-Amz-Security-Token,X-Requested-With",
    "Access-Control-Allow-Credentials": "true",
}


# ---------------------------------------------------------------------------- #
#                               HELPER FUNCTIONS                               #
# ---------------------------------------------------------------------------- #

def decimal_serializer(obj):
    """
    Convert DynamoDB Decimal values into JSON serializable values.

    DynamoDB numbers are returned by boto3 as Decimal objects.
    Whole numbers are converted to int and decimal numbers to float.
    """
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)

        return float(obj)

    raise TypeError(
        f"Object of type {obj.__class__.__name__} "
        "is not JSON serializable"
    )


def normalize_string(value: str | None) -> str:
    """
    Normalize strings used by the backend.

    All values are stripped and converted to lowercase.
    """
    return str(value or "").strip().lower()


def get_request_by_id(request_id: str) -> dict | None:
    """
    Retrieve a maintenance request by its request ID.

    The maintenance request table uses:
        PK: id
        SK: jobCreated

    Since only the partition key is known at this stage, query for the
    request ID and return the first matching item.
    """
    response = table_requests.query(
        KeyConditionExpression=Key("id").eq(request_id),
        Limit=1,
    )

    items = response.get("Items", [])

    return items[0] if items else None


def get_locations() -> dict[str, str]:
    """
    Retrieve all locations and their location codes from DynamoDB.

    The locations table is the source of truth for valid locations.
    This removes the need to maintain a hard-coded location dictionary
    in every Lambda.

    Expected DynamoDB items:

        {
            "location": "maitland",
            "code": "VTR"
        }

    Returns:
        {
            "maitland": "VTR",
            "bellville": "BTX",
            ...
        }

    Location names are normalized to lowercase to match the backend
    storage format.

    Pagination is handled in case the table grows beyond a single
    DynamoDB scan response.
    """
    locations = {}
    last_evaluated_key = None

    try:
        while True:

            params = {
                "ProjectionExpression": "#loc, #code",
                "ExpressionAttributeNames": {
                    "#loc": "location",
                    "#code": "code",
                },
            }

            if last_evaluated_key:
                params["ExclusiveStartKey"] = last_evaluated_key

            response = table_locations.scan(**params)

            for item in response.get("Items", []):

                location = normalize_string(item.get("location"))
                code = str(item.get("code") or "").strip().upper()

                # Only add valid location/code combinations.
                if location and code:
                    locations[location] = code

            last_evaluated_key = response.get("LastEvaluatedKey")

            if not last_evaluated_key:
                break

        return locations

    except ClientError as exc:
        print(
            "Error retrieving locations:",
            exc.response.get("Error", {}).get("Message", str(exc)),
        )
        raise


def get_cape_town_now() -> datetime:
    """
    Return the current Cape Town/SAST date and time.
    """
    sast = timezone(timedelta(hours=2))

    return datetime.now(timezone.utc).astimezone(sast)


def get_month_bounds():
    """
    Return the start of the current month, start of next month,
    and YYYYMM code using Cape Town time.
    """
    now_ct = get_cape_town_now()

    start_of_month = now_ct.replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    if now_ct.month == 12:
        next_month = now_ct.replace(
            year=now_ct.year + 1,
            month=1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

    else:
        next_month = now_ct.replace(
            month=now_ct.month + 1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

    current_month_code = now_ct.strftime("%Y%m")

    return (
        start_of_month.isoformat(),
        next_month.isoformat(),
        current_month_code,
    )


def get_monthly_jobcard_count(location: str) -> int:
    """
    Return the number of maintenance requests for a location
    during the current month.
    """
    start_date, end_date, _ = get_month_bounds()

    total_count = 0
    last_evaluated_key = None

    while True:

        params = {
            "IndexName": "LocationIndex",
            "KeyConditionExpression": (
                Key("location").eq(normalize_string(location))
                & Key("jobCreated").between(start_date, end_date)
            ),
            "Select": "COUNT",
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
    Generate the next jobcard number for a location.

    Location information is retrieved from the locations DynamoDB table
    instead of using a hard-coded dictionary.

    Format:
        Job-<LOCATION_CODE>-<YYYYMM>-<SEQUENCE>

    Example:
        Job-VTR-202610-0001
    """

    # Normalize the location stored on the maintenance request.
    normalized_location = normalize_string(location)

    # Retrieve the latest location/code mappings from DynamoDB.
    locations = get_locations()

    # Resolve the location code from the locations table.
    location_code = locations.get(normalized_location)

    if not location_code:
        raise ValueError(
            f"Location '{normalized_location}' does not have "
            "a valid code in the locations table"
        )

    _, _, job_date = get_month_bounds()

    counter_id = f"JOBCARD#{location_code}#{job_date}"

    now_iso = datetime.now(timezone.utc).isoformat()

    response = table_jobcard_sequence.update_item(
        Key={
            "id": counter_id,
        },
        UpdateExpression="""
            SET lastSequence = if_not_exists(lastSequence, :zero) + :inc,
                lastRequestId = :request_id,
                updatedAt = :updated_at
        """,
        ExpressionAttributeValues={
            ":zero": 0,
            ":inc": 1,
            ":request_id": request_id,
            ":updated_at": now_iso,
        },
        ReturnValues="UPDATED_NEW",
    )

    next_number = int(
        response["Attributes"]["lastSequence"]
    )

    return (
        f"Job-{location_code}-"
        f"{job_date}-"
        f"{next_number:04d}"
    )


def generate_test_event(event: dict) -> str:
    """
    Serialize a Lambda event into a compact JSON string that can be
    copied from CloudWatch and reused as a Lambda test event.
    """
    return json.dumps(
        event,
        separators=(",", ":"),
        default=decimal_serializer,
    )


# ---------------------------------------------------------------------------- #
#                               LAMBDA HANDLER                                 #
# ---------------------------------------------------------------------------- #

def lambda_handler(event, context):
    """
    Process maintenance request status updates and approvals.

    When the incoming status is "Approved":

        - status becomes "in progress"
        - technician/user assignment information is added
        - target date is added
        - approval metadata is added
        - a new jobcard number is generated

    Location codes are dynamically retrieved from the locations table.
    """

    try:

        # -------------------------------------------------------------------- #
        # Validate request body
        # -------------------------------------------------------------------- #

        if not event.get("body"):
            return _response(
                400,
                {
                    "message": "Missing request body",
                },
            )

        data = json.loads(event["body"])

        claims = (
            event
            .get("requestContext", {})
            .get("authorizer", {})
            .get("claims", {})
        )

        required_fields = [
            "targetDate",
            "status",
            "selectedRowId",
            "assign_to_name",
            "assign_to_sub",
            "assign_to_group",
        ]

        for field in required_fields:

            if field not in data or data[field] == "":
                return _response(
                    400,
                    {
                        "message": f"Missing field: {field}",
                    },
                )

        # -------------------------------------------------------------------- #
        # Normalize request data
        # -------------------------------------------------------------------- #

        request_id = str(
            data["selectedRowId"]
        ).strip()

        action_status = normalize_string(
            data.get("status")
        )

        target_date = str(
            data["targetDate"]
        ).strip()

        assign_to_name = normalize_string(
            data.get("assign_to_name")
        )

        assign_to_sub = str(
            data.get("assign_to_sub") or ""
        ).strip()

        assign_to_group = normalize_string(
            data.get("assign_to_group")
        )

        # -------------------------------------------------------------------- #
        # Status timestamp
        # -------------------------------------------------------------------- #

        status_updated_at = (
            get_cape_town_now().isoformat()
        )

        # -------------------------------------------------------------------- #
        # Retrieve existing maintenance request
        # -------------------------------------------------------------------- #

        existing_item = get_request_by_id(
            request_id
        )

        if not existing_item:
            return _response(
                404,
                {
                    "message": "Request not found",
                },
            )

        job_created = existing_item.get(
            "jobCreated"
        )

        if not job_created:
            return _response(
                500,
                {
                    "message":
                        "Existing item missing jobCreated",
                },
            )

        # -------------------------------------------------------------------- #
        # Get the request location
        # -------------------------------------------------------------------- #

        location = normalize_string(
            existing_item.get("location")
        )

        if (
            action_status == "approved"
            and not location
        ):
            return _response(
                500,
                {
                    "message":
                        "Location not found on maintenance request",
                },
            )

        # -------------------------------------------------------------------- #
        # Translate frontend action into database status
        # -------------------------------------------------------------------- #

        db_status = (
            "in progress"
            if action_status == "approved"
            else action_status
        )

        # -------------------------------------------------------------------- #
        # Base update
        # -------------------------------------------------------------------- #

        update_expression = """
            SET #s = :status,
                #td = :targetDate,
                #an = :assign_to_name,
                #as = :assign_to_sub,
                #ag = :assign_to_group,
                #su = :statusUpdatedAt
        """

        expression_attribute_names = {
            "#s": "status",
            "#td": "targetDate",
            "#an": "assign_to_name",
            "#as": "assign_to_sub",
            "#ag": "assign_to_group",
            "#su": "statusUpdatedAt",
        }

        expression_attribute_values = {
            ":status": db_status,
            ":targetDate": target_date,
            ":assign_to_name": assign_to_name,
            ":assign_to_sub": assign_to_sub,
            ":assign_to_group": assign_to_group,
            ":statusUpdatedAt": status_updated_at,
        }

        condition_expression = (
            "attribute_exists(id) "
            "AND attribute_exists(jobCreated)"
        )

        # -------------------------------------------------------------------- #
        # Approval-specific data
        # -------------------------------------------------------------------- #

        if action_status == "approved":

            # --------------------------------------------------------------- #
            # Dynamically retrieve the location code and generate jobcard
            # --------------------------------------------------------------- #

            jobcard_number = generate_jobcard_no(
                location,
                request_id,
            )

            approved_at = (
                datetime.now(timezone.utc)
                .isoformat()
            )

            approved_by = (
                f'{claims.get("name", "").strip()} '
                f'{claims.get("family_name", "").strip()}'
            ).strip()

            approved_by_sub = (
                claims.get("sub", "")
            )

            update_expression += """,
                approved_at = :approved_at,
                approved_by = :approved_by,
                approved_by_sub = :approved_by_sub,
                jobcardNumber = :jobcardNumber
            """

            expression_attribute_values[
                ":approved_at"
            ] = approved_at

            expression_attribute_values[
                ":approved_by"
            ] = approved_by

            expression_attribute_values[
                ":approved_by_sub"
            ] = approved_by_sub

            expression_attribute_values[
                ":jobcardNumber"
            ] = jobcard_number

            # Prevent the same request from receiving another jobcard number.
            condition_expression += (
                " AND attribute_not_exists(jobcardNumber)"
            )

        # -------------------------------------------------------------------- #
        # Update maintenance request
        # -------------------------------------------------------------------- #

        response = table_requests.update_item(
            Key={
                "id": request_id,
                "jobCreated": job_created,
            },
            UpdateExpression=update_expression,
            ExpressionAttributeNames=(
                expression_attribute_names
            ),
            ExpressionAttributeValues=(
                expression_attribute_values
            ),
            ConditionExpression=condition_expression,
            ReturnValues="ALL_NEW",
        )

        # -------------------------------------------------------------------- #
        # Response
        # -------------------------------------------------------------------- #

        return _response(
            200,
            {
                "message":
                    "Request updated successfully",
                "data": response.get(
                    "Attributes",
                    {},
                ),
            },
        )

    # ------------------------------------------------------------------------ #
    # DynamoDB Errors
    # ------------------------------------------------------------------------ #

    except ClientError as exc:

        error_code = (
            exc.response
            .get("Error", {})
            .get("Code")
        )

        if (
            error_code
            == "ConditionalCheckFailedException"
        ):
            return _response(
                409,
                {
                    "message":
                        "Request could not be updated. "
                        "It may already have been approved.",
                },
            )

        print(
            "DynamoDB Error:",
            exc.response.get("Error", {}),
        )

        return _response(
            500,
            {
                "message": "Database error",
            },
        )

    # ------------------------------------------------------------------------ #
    # Validation / Location Errors
    # ------------------------------------------------------------------------ #

    except ValueError as exc:

        print(
            "Validation Error:",
            str(exc),
        )

        return _response(
            400,
            {
                "message": str(exc),
            },
        )

    # ------------------------------------------------------------------------ #
    # Unexpected Errors
    # ------------------------------------------------------------------------ #

    except Exception as exc:

        print(
            "Error:",
            str(exc),
        )

        return _response(
            500,
            {
                "message":
                    "Internal server error",
            },
        )


# ---------------------------------------------------------------------------- #
#                                  RESPONSE                                    #
# ---------------------------------------------------------------------------- #

def _response(status_code, body):
    """
    Build an API Gateway response.

    decimal_serializer is required because DynamoDB returns numeric
    attributes as Decimal objects.
    """
    return {
        "statusCode": status_code,
        "headers": HEADERS,
        "body": json.dumps(
            body,
            default=decimal_serializer,
        ),
    }
