import boto3
import json
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor

lambda_client = boto3.client("lambda")
dynamodb = boto3.resource("dynamodb")

users_table = dynamodb.Table("crud-nosql-app-users-table")

# ======================================================================================
# User Helpers
# ======================================================================================


def decimal_serializer(obj):
    """
    Custom JSON serializer for handling DynamoDB Decimal types.

    Args:
        obj: Object to serialize.

    Returns:
        int | float: Converted numeric value.

    Raises:
        TypeError: If object type is not supported.
    """
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    raise TypeError


# ======================================================================================
# Get the claims for the user
# ======================================================================================

def get_user_claims(event):
    """
    Extract user claims and location from the event.

    Args:
        event (dict): The event data passed to the Lambda function.

    Returns:
        tuple: A tuple containing (claims, location).
               - claims (dict): User claims from the event.
               - location (dict): Location details from the event.
    """
    print("Event:", json.dumps(event))

    # Extract claims from the event
    claims = event.get("requestContext", {}).get(
        "authorizer", {}).get("claims", {})

    return claims

# ======================================================================================
# Get the user sub
# ======================================================================================


def get_user_by_sub(user_sub):

    if not user_sub:
        return None

    response = users_table.get_item(
        Key={
            "id": user_sub
        }
    )

    return response.get("Item")


def handle_request_metadata(event):
    """
    Extract HTTP method and construct CORS headers based on request origin.

    Args:
        event (dict): Lambda event payload.

    Returns:
        tuple:
            method (str): HTTP method (GET, POST, OPTIONS, etc.)
            response_headers (dict): CORS-enabled response headers.
    """
    headers = event.get("headers") or {}
    origin = headers.get("origin") or headers.get("Origin") or ""

    allowed_origins = [
        "https://www.crud-nosql.app.fabian-portfolio.net",
        "https://crud-nosql.app.fabian-portfolio.net",
        "http://localhost:5173",
    ]

    allowed_origin = origin if origin in allowed_origins else ""

    response_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": allowed_origin,
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Credentials": "true",
    }

    method = (
        event.get("httpMethod")
        or event.get("requestContext", {}).get("http", {}).get("method")
    )

    return method, response_headers


def handle_options_request(method, headers):
    """
    Handle CORS preflight (OPTIONS) requests.

    Args:
        method (str): HTTP method.
        headers (dict): Response headers.

    Returns:
        dict | None: HTTP response if OPTIONS request, otherwise None.
    """
    if method == "OPTIONS":
        return _response(200, {"message": "Success"}, headers)
    return None


def invoke_lambda(function_name, event):
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(event).encode(),
    )

    payload = json.loads(
        response["Payload"].read()
    )

    return json.loads(payload["body"])


def lambda_handler(event, context):
    """
    AWS Lambda handler for fetching dashboard metrics from multiple services.

    This function aggregates metrics from various microservices by invoking
    their respective Lambda functions concurrently using ThreadPoolExecutor.

    Args:
        event (dict): The event data passed to the Lambda function.
        context (object): Runtime information of the Lambda function.

    Returns:
        dict: A formatted HTTP response containing aggregated metrics and necessary CORS headers.
    """
    print("event:", json.dumps(event))

    # CORS
    method, HEADERS = handle_request_metadata(event)

    options_response = handle_options_request(method, HEADERS)
    if options_response:
        return options_response

    claims = get_user_claims(event)
    user_sub = claims.get("sub")

    user_record = get_user_by_sub(user_sub)

    if not user_record:
        return _response(
            404,
            {"message": "User not found"},
            HEADERS
        )

    group = user_record.get("group")
    location = user_record.get("location")

    functions = {
        "storeCost": "getStoreCostMetrics",
        "storeJobs": "getStoreJobMetrics",
        "cards": "getCardMetrics",
        "verification": "getVerificationMetrics",
        # "assets": "getAssetMetrics",
        # "transfers": "getTransferMetrics",
    }

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            name: executor.submit(
                invoke_lambda,
                function_name,
                event
            )
            for name, function_name in functions.items()
        }

        user = {
            "role": group,
            "location": location
        }

        data = {
            "user": user,
            **{
                name: future.result()
                for name, future in futures.items()
            }
        }

    return _response(200, data, HEADERS)

# ----------------------------
# Response helper
# ----------------------------


def _response(status_code, body, headers):
    """
    Construct a standard API Gateway HTTP response.

    Args:
        status_code (int): HTTP status code.
        body (dict | list): Response payload.
        headers (dict): HTTP headers.

    Returns:
        dict: Formatted response object.
    """
    return {
        "statusCode": status_code,
        "body": json.dumps(body, default=decimal_serializer),
        "headers": headers,
    }
