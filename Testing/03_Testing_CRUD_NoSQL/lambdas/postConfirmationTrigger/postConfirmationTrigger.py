import boto3
from datetime import datetime, timezone

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("crud-nosql-app-users-table")

def to_human_date(iso_string: str) -> str:
    dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    return dt.strftime("%d %b %Y, %H:%M")

def lambda_handler(event, context):
    try:
        user_attributes = event["request"]["userAttributes"]

        sub = user_attributes["sub"]

        now = datetime.now(timezone.utc).isoformat()

        table.update_item(
            Key={"id": sub},
            UpdateExpression="""
                SET #status = :status,
                    updatedAt = :updatedAt
            """,
            ExpressionAttributeNames={
                "#status": "status"
            },
            ExpressionAttributeValues={
                ":status": "CONFIRMED",
                ":updatedAt": to_human_date(now)
            }
        )

        return event

    except Exception as e:
        print(f"Error updating DynamoDB: {str(e)}")
        raise e