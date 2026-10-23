import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Key
from datetime import datetime, timedelta

dynamodb = boto3.resource("dynamodb")

TABLE_ASSETS = "crud-nosql-app-assets-table"
TABLE_VERIFICATIONS = "crud-nosql-app-assets-verification-table"

table_assets = dynamodb.Table(TABLE_ASSETS)
table_verifications = dynamodb.Table(TABLE_VERIFICATIONS)

# $  1. Update asset verified by barcode with an dynamodb event stream to eventbridge


def set_next_verification_date(verification_date: str) -> str:
    verification_dt = datetime.fromisoformat(verification_date)

    next_verification_date = verification_dt + timedelta(days=180)

    return next_verification_date.isoformat()


def update_assets_table(
    table_assets,
    asset_id: str,
    asset_uuid: str | None,
    verification_time: str,
    verifier_name: str,
    verified_location,
):
    # Manual verification addresses assets by UUID because a barcode can be
    # absent. Existing barcode verification events continue to use the GSI.
    if asset_uuid:
        asset = table_assets.get_item(Key={"id": asset_uuid}).get("Item")
    else:
        response = table_assets.query(
            IndexName="AssetIDIndex",
            KeyConditionExpression=Key("assetID").eq(asset_id),
            Limit=1,
        )
        items = response.get("Items", [])
        asset = items[0] if items else None

    if not asset:
        raise Exception(
            f"Asset not found for verification identity {asset_uuid or asset_id}"
        )
    next_verification_due = set_next_verification_date(verification_time)
    print('next_verification_due:', next_verification_due)

    table_assets.update_item(
        Key={"id": asset["id"]},
        UpdateExpression="""
            SET verify_status = :verify_status,
                last_verified_at = :time,
                verified_by = :user,
                verified_location = :verified_location,
                next_verification_due = :next_verification_due
        """,
        ExpressionAttributeValues={
            ":verify_status": "verified",
            ":time": verification_time,
            ":user": verifier_name,
            ":verified_location": verified_location,
            ":next_verification_due": next_verification_due,
        },
    )

    return {
        "asset_id": asset_id,
        "verify_status": "verified",
    }

# This function are invoked periodically to check the status of the assets and update their status according to the last_verification date


# def check_asset_verification_status():
#     VERIFCATION_STATUS = ["verified", "pending", "overdue", "due soon"]
#     print(VERIFCATION_STATUS)


def normalize_string(value: str | None) -> str:
    return str(value or "").strip().lower()


def lambda_handler(event, context):
    print("event:", event)

    try:
        new_image = event["detail"]["dynamodb"]["NewImage"]
        asset_id = new_image["assetID"]["S"]

        asset_uuid = new_image.get("assetUuid", {}).get("S")
        position = new_image.get("position", {}).get("M")
        if position:
            verified_location = {
                "latitude": Decimal(position["latitude"]["N"]),
                "longitude": Decimal(position["longitude"]["N"]),
            }
        else:
            verified_location = new_image.get("location", {}).get("S", "")

        response = update_assets_table(
            table_assets=table_assets,
            asset_id=asset_id,
            asset_uuid=asset_uuid,
            verification_time=new_image["verificationCreated"]["S"],
            verifier_name=new_image["verified_by"]["S"],
            verified_location=verified_location,
        )
        print('response:', response)
        return {
            "status": "success",
            "assetID": asset_id,
            "message": f"Asset {asset_id} successfully verified"
        }

    except Exception as exc:
        print("Error:", exc)
        return {
            "success": False,
            "error": str(exc)
        }
