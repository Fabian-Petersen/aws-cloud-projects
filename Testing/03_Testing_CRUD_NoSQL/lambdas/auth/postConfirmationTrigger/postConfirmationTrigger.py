import boto3
import json
from datetime import datetime, timezone, timedelta

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("crud-nosql-app-users-table")


HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Access-Control-Allow-Methods": "DELETE, OPTIONS, POST",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token,X-Requested-With",
    "Access-Control-Allow-Credentials": "true"
}


def lambda_handler(event, context):
    """Mark the authenticated Cognito user as confirmed in DynamoDB."""
    print("event:", json.dumps(event))
    try:
        # Extract sub from Cognito authorizer claims
        claims = event.get("requestContext", {}).get(
            "authorizer", {}).get("claims", {})
        user_id = claims.get("sub")

        if not user_id:
            return _response(400, {"message": "no user id found in token"})

        SAST = timezone(timedelta(hours=2))
        now = datetime.now(SAST).isoformat()

        table.update_item(
            Key={"id": user_id},
            UpdateExpression="SET #status = :status, updatedAt = :updatedAt",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "CONFIRMED",
                ":updatedAt": now,
            },
        )

        return _response(200, {"message": "user status successfully updated"})

    except Exception as e:
        print(f"Error updating DynamoDB: {str(e)}")
        return _response(500, {"message": "internal server error"})


def _response(status_code: int, body: dict) -> dict:
    """Build a JSON API Gateway proxy response with the endpoint CORS headers.

    Args:
        status_code: HTTP status code returned to the client.
        body: JSON-serializable response payload.

    Returns:
        A mapping containing ``statusCode``, the shared response headers, and a
        JSON-encoded ``body``.
    """
    return {
        "statusCode": status_code,
        "headers": HEADERS,
        "body": json.dumps(body, default=str),
    }
