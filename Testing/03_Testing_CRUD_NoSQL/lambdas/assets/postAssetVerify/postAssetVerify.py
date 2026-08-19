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


def asset_exists(asset_id: str) -> dict | None:
    """
    Returns asset item if exists, otherwise None
    """
    res = table_assets.query(
        IndexName="AssetIDIndex",
        KeyConditionExpression=Key("assetID").eq(asset_id),
        Limit=1,
    )

    items = res.get("Items", [])
    return items[0] if items else None


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
        # $ OPTIONS support
        if event.get("httpMethod") == "OPTIONS":
            return _response(200, {"message": "OK"})

        if not event.get("body"):
            return _response(400, {"message": "Missing body"})

        body = json.loads(event["body"])
        print("body:", body)

        # $ Path param: api/assets/{id}/verify
        asset_id = event.get("pathParameters", {}).get("id")
        if not asset_id:
            return _response(400, {"message": "Missing asset id"})
        print(f"Asset ID: {asset_id}")

        # $ Cognito claims
        claims = event.get("requestContext", {}).get(
            "authorizer", {}).get("claims", {})
        user_id = claims.get("sub")

        if not user_id:
            return _response(401, {"message": "Unauthorized"})

        verifier_name = get_user_name(user_id)

        # $ required payload fields
        required = ["latitude", "longitude"]
        for f in required:
            if f not in body:
                return _response(400, {"message": f"Missing position coordinates field: {f}"})

        # $ STEP 1: Validate asset exists BEFORE writing anything
        asset = asset_exists(asset_id)

        if not asset:
            response = _response(
                404,
                {"message": f"Asset {asset_id} not registered in the database"}
            )

            print("response:", response)
            return response

        # $ STEP 2. Proceed with verification write (audit trail)
        verification_id = str(uuid.uuid4())
        now = datetime.now(timezone(timedelta(hours=2))).isoformat()
        latitude = Decimal(str(body["latitude"]))
        longitude = Decimal(str(body["longitude"]))

        verification_item = {
            "assetID": asset_id,  # PKs
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
                "message": f"Asset {asset_id} successfully verified",
            },
        )

    except Exception as e:
        print("Error:", str(e))
        return _response(500, {"message": "Internal server error"})
