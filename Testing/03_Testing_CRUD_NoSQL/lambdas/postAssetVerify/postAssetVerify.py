import json
import boto3
import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")

TABLE_USERS = "crud-nosql-app-users-table"
TABLE_ASSETS = "crud-nosql-app-assets-table"
TABLE_VERIFICATIONS = "crud-nosql-app-assets-verification-table"

table_users = dynamodb.Table(TABLE_USERS)
table_assets = dynamodb.Table(TABLE_ASSETS)
table_verifications = dynamodb.Table(TABLE_VERIFICATIONS)


HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
}


def decimal_serializer(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError


def _response(status_code, body, headers=HEADERS):
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body, default=decimal_serializer),
    }


def get_user_name(user_id: str) -> str:
    """
    Fetch full name from Users table using Cognito sub (user_id)
    """
    res = table_users.get_item(Key={"id": user_id})
    user = res.get("Item", {})

    first = user.get("name", "")
    last = user.get("family_name", "")

    return f"{first} {last}".strip()


def lambda_handler(event, context):
    try:
        # OPTIONS support
        if event.get("httpMethod") == "OPTIONS":
            return _response(200, {"message": "OK"})

        if not event.get("body"):
            return _response(400, {"message": "Missing body"})

        body = json.loads(event["body"])

        # Path param: api/assets/{id}/verify
        asset_id = event.get("pathParameters", {}).get("id")
        if not asset_id:
            return _response(400, {"message": "Missing asset id"})

        # Cognito claims
        claims = event.get("requestContext", {}).get(
            "authorizer", {}).get("claims", {})
        user_id = claims.get("sub")

        if not user_id:
            return _response(401, {"message": "Unauthorized"})

        verifier_name = get_user_name(user_id)

        # required payload fields
        required = ["latitude", "longitude"]
        for f in required:
            if f not in body:
                return _response(400, {"message": f"Missing field: {f}"})

        verification_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        latitude = Decimal(str(body["latitude"]))
        longitude = Decimal(str(body["longitude"]))

        # $  1. Update asset status: This will be done by the updateAssetVerificationStatus lambda
        # table_assets.update_item(
        #     Key={"id": asset_id},
        #     UpdateExpression="""
        #         SET #s = :status,
        #             verified = :verified,
        #             last_verified = :time,
        #             verified_by = :user
        #     """,
        #     ExpressionAttributeNames={"#s": "status"},
        #     ExpressionAttributeValues={
        #         ":status": "verified",
        #         ":verified": True,
        #         ":time": now,
        #         ":user": verifier_name,
        #     },
        # )

        # 2. Write verification record (audit trail)
        verification_item = {
            "assetID": asset_id,  # PK
            "verificationCreated": now,  # SK
            "id": verification_id,
            "verified_by": verifier_name,
            "verifier_id": user_id,
            "position": {
                "latitude": latitude,
                "longitude": longitude
            }
        }

        table_verifications.put_item(Item=verification_item)

        return _response(
            200,
            {
                "message": "Asset verified successfully",
            },
        )

    except Exception as e:
        print("Error:", str(e))
        return _response(500, {"message": "Internal server error"})
