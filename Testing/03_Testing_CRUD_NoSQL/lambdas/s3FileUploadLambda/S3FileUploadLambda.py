# $ This lambda function handles the file uploads to the s3 bucket and updates the dynamoDB images field

import boto3
from urllib.parse import unquote_plus
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")

MAINTENANCE_TABLE = dynamodb.Table("crud-nosql-app-maintenance-request-table")
ASSETS_TABLE = dynamodb.Table("crud-nosql-app-assets-table")
ACTION_TABLE = dynamodb.Table("crud-nosql-app-maintenance-action-table"
                              )
TRANSFER_TABLE = dynamodb.Table("crud-nosql-app-assets-transfer-table"
                                )


def get_maintenance_sort_key(item_id: str):
    response = MAINTENANCE_TABLE.query(
        KeyConditionExpression=Key("id").eq(item_id),
        Limit=1
    )
    items = response.get("Items", [])
    if not items:
        return None
    return items[0].get("jobCreated")


def get_action_sort_key(item_id: str):
    response = ACTION_TABLE.query(
        KeyConditionExpression=Key("id").eq(item_id),
        Limit=1
    )

    items = response.get("Items", [])

    if not items:
        return None

    return items[0].get("actionCreated")


def get_transfers_sort_key(item_id: str):
    response = TRANSFER_TABLE.query(
        KeyConditionExpression=Key("id").eq(item_id),
        Limit=1
    )

    items = response.get("Items", [])

    if not items:
        return None

    return items[0].get("transferCreated")


def append_file_to_table(
    table,
    key,
    attribute_name,
    file_data
):
    table.update_item(
        Key=key,
        UpdateExpression=f"""
            SET {attribute_name} = list_append(
                if_not_exists({attribute_name}, :empty),
                :file
            )
        """,
        ExpressionAttributeValues={
            ":file": [file_data],
            ":empty": []
        }
    )


def lambda_handler(event, context):
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])

        parts = key.split("/")

        if len(parts) < 3:
            continue

        prefix = parts[0]
        item_id = parts[1]
        filename = parts[-1]

        file_data = {
            "bucket": bucket,
            "key": key,
            "filename": filename,
        }

        # =========================
        # Maintenance request images
        # =========================
        if prefix == "maintenance":

            job_created = get_maintenance_sort_key(item_id)

            if not job_created:
                print(f"No maintenance item found for id={item_id}")
                continue

            append_file_to_table(
                table=MAINTENANCE_TABLE,
                key={
                    "id": item_id,
                    "jobCreated": job_created
                },
                attribute_name="images",
                file_data=file_data
            )

        # =========================
        # Maintenance action images
        # =========================
        elif prefix == "maintenance_action":

            action_created = get_action_sort_key(item_id)

            if not action_created:
                print(f"No action item found for id={item_id}")
                continue

            append_file_to_table(
                table=ACTION_TABLE,
                key={
                    "id": item_id,
                    "actionCreated": action_created
                },
                attribute_name="images",
                file_data=file_data
            )

        # =========================
        # Maintenance invoices
        # =========================
        elif prefix == "invoices":

            action_created = get_action_sort_key(item_id)

            if not action_created:
                print(f"No action item found for id={item_id}")
                continue

            append_file_to_table(
                table=ACTION_TABLE,
                key={
                    "id": item_id,
                    "actionCreated": action_created
                },
                attribute_name="invoices",
                file_data=file_data
            )

        # =========================
        # Transfer invoices
        # =========================
        elif prefix == "invoices":

            transfer_created = get_transfers_sort_key(item_id)

            if not transfer_created:
                print(f"No transfer item found for id={item_id}")
                continue

            append_file_to_table(
                table=TRANSFER_TABLE,
                key={
                    "id": item_id,
                    "transferCreated": transfer_created
                },
                attribute_name="invoices",
                file_data=file_data
            )

        # =========================
        # Asset images
        # =========================
        elif prefix == "assets":

            append_file_to_table(
                table=ASSETS_TABLE,
                key={"id": item_id},
                attribute_name="images",
                file_data=file_data
            )
