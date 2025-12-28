import json
import uuid
from datetime import datetime, timezone

import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("crud-nosql-app-maintenance-request-table")


def lambda_handler(event, context):
    try:
        if "body" not in event or not event["body"]:
            return _response(400, {"message": "Missing request body"})

        body = json.loads(event["body"])

        required_fields = [
            "description",
            "store",
            "type",
            "priority",
            "equipment",
            "impact",
        ]

        for field in required_fields:
            if not body.get(field):
                return _response(400, {"message": f"Missing field: {field}"})

        # Cognito user claims (trusted source)
        # claims = (
        #     event.get("requestContext", {})
        #     .get("authorizer", {})
        #     .get("claims")
        # )

        # if not claims:
        #     return _response(401, {"message": "Unauthorized"})

        item = {
            "id": str(uuid.uuid4()),
            "createdAt": datetime.now(timezone.utc).isoformat(),

            # User details
            # "userId": claims.get("sub"),
            # "userEmail": claims.get("email"),
            # "userName": claims.get("name"),

            # Payload
            "description": body["description"],
            "store": body["store"],
            "type": body["type"],
            "priority": body["priority"],
            "equipment": body["equipment"],
            "impact": body["impact"],
            "images": body.get("images", []),
        }

        table.put_item(Item=item)

        return _response(200, item)

    except Exception as exc:
        print("Error creating maintenance request:", exc)
        return _response(500, {"message": "Internal server error"})


def _response(status_code: int, body: dict):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(body),
    }