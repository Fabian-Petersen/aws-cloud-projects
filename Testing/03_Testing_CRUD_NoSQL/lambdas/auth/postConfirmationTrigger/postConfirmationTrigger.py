import boto3
import json
from datetime import datetime, timezone, timedelta

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("crud-nosql-app-users-table")

def to_human_date(iso_string: str) -> str:
    SAST = timezone(timedelta(hours=2))
    dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    return dt.astimezone(SAST).strftime("%d %b %Y, %H:%M")

def lambda_handler(event, context):
    print("event:", event)
    try:
        # Extract sub from Cognito authorizer claims
        claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
        user_id = claims.get("sub")

        if not user_id:
            return _response(400, {"message": "no user id found in token"})

        now = datetime.now(timezone.utc).isoformat()

        table.update_item(
            Key={"id": user_id},
            UpdateExpression="SET #status = :status, updatedAt = :updatedAt",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "CONFIRMED",
                ":updatedAt": to_human_date(now),
            },
        )

        return _response(200, {"message": "user status successfully updated"})

    except Exception as e:
        print(f"Error updating DynamoDB: {str(e)}")
        return _response(500, {"message": "internal server error"})


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=str),
    }