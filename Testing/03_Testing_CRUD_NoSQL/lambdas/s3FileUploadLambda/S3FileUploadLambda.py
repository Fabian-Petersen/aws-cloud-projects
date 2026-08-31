import boto3
import json
from urllib.parse import unquote_plus
from boto3.dynamodb.conditions import Key


dynamodb = boto3.resource("dynamodb")

MAINTENANCE_TABLE = dynamodb.Table(
    "crud-nosql-app-maintenance-request-table"
)

ASSETS_TABLE = dynamodb.Table(
    "crud-nosql-app-assets-table"
)

ACTION_TABLE = dynamodb.Table(
    "crud-nosql-app-maintenance-action-table"
)

TRANSFER_TABLE = dynamodb.Table(
    "crud-nosql-app-assets-transfer-table"
)


# ============================================================
# Sort-key lookups
# ============================================================

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
        KeyConditionExpression=Key("transferId").eq(item_id),
        Limit=1
    )

    items = response.get("Items", [])

    if not items:
        return None

    return items[0].get("transferCreated")


# ============================================================
# Generic list append
# ============================================================

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


# ============================================================
# Transfer asset image
# ============================================================

def append_transfer_asset_image(
    transfer_id,
    transfer_created,
    asset_index,
    file_data
):
    """
    Atomically append an uploaded image to the images array
    of the asset at asset_index.
    """

    response = TRANSFER_TABLE.get_item(
        Key={
            "transferId": transfer_id,
            "transferCreated": transfer_created
        },
        ProjectionExpression="assets"
    )

    item = response.get("Item")

    if not item:
        print(
            f"No transfer found for "
            f"transferId={transfer_id}, "
            f"transferCreated={transfer_created}"
        )
        return

    assets = item.get("assets", [])

    # Validate the index before updating DynamoDB
    if not isinstance(asset_index, int):
        print(
            f"Invalid asset index: {asset_index}"
        )
        return

    if asset_index < 0 or asset_index >= len(assets):
        print(
            f"Asset index {asset_index} out of range "
            f"for transfer {transfer_id}. "
            f"Asset count: {len(assets)}"
        )
        return

    image_path = f"assets[{asset_index}].images"

    TRANSFER_TABLE.update_item(
        Key={
            "transferId": transfer_id,
            "transferCreated": transfer_created
        },
        UpdateExpression=(
            f"SET {image_path} = list_append("
            f"if_not_exists({image_path}, :empty), "
            f":file)"
        ),
        ExpressionAttributeValues={
            ":file": [file_data],
            ":empty": []
        }
    )

    print(
        f"Added image {file_data['key']} "
        f"to asset index {asset_index} "
        f"in transfer {transfer_id}"
    )

# ============================================================
# Lambda
# ============================================================


def lambda_handler(event, context):
    print("event", json.dumps(event))

    for record in event.get("Records", []):

        try:
            bucket = record["s3"]["bucket"]["name"]

            key = unquote_plus(
                record["s3"]["object"]["key"]
            )

            parts = key.split("/")

            if len(parts) < 3:
                print(f"Skipping invalid S3 key: {key}")
                continue

            prefix = parts[0]

            filename = parts[-1]

            file_data = {
                "bucket": bucket,
                "key": key,
                "filename": filename,
            }

            # ====================================================
            # Maintenance request images
            #
            # maintenance/{id}/{filename}
            # ====================================================

            if prefix == "maintenance":

                item_id = parts[1]

                job_created = get_maintenance_sort_key(
                    item_id
                )

                if not job_created:
                    print(
                        f"No maintenance item found "
                        f"for id={item_id}"
                    )
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

            # ====================================================
            # Maintenance action images
            #
            # maintenance_action/{id}/{filename}
            # ====================================================

            elif prefix == "maintenance_action":

                item_id = parts[1]

                action_created = get_action_sort_key(
                    item_id
                )

                if not action_created:
                    print(
                        f"No action item found "
                        f"for id={item_id}"
                    )
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

            # ====================================================
            # Maintenance invoices
            #
            # invoices/{actionId}/{filename}
            # ====================================================

            elif prefix == "invoices":

                item_id = parts[1]

                action_created = get_action_sort_key(
                    item_id
                )

                if not action_created:
                    print(
                        f"No action item found "
                        f"for id={item_id}"
                    )
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

            # ====================================================
            # Transfers
            #
            # transfers/{transferId}/...
            # ====================================================

            elif prefix == "transfers":

                transfer_id = parts[1]

                transfer_created = get_transfers_sort_key(
                    transfer_id
                )

                if not transfer_created:
                    print(
                        f"No transfer found "
                        f"for transferId={transfer_id}"
                    )
                    continue

                # ------------------------------------------------
                # Transfer transport invoice
                #
                # transfers/{transferId}/invoices/{filename}
                # ------------------------------------------------

                if (
                    len(parts) >= 4
                    and parts[2] == "invoices"
                ):

                    append_file_to_table(
                        table=TRANSFER_TABLE,
                        key={
                            "transferId": transfer_id,
                            "transferCreated": transfer_created
                        },
                        attribute_name="transportInvoices",
                        file_data=file_data
                    )

                # ------------------------------------------------
                # Transfer asset image
                #
                # transfers/{transferId}/
                # assets/{asset_index}/images/{filename}
                # ------------------------------------------------

                elif (
                    len(parts) >= 6
                    and parts[2] == "assets"
                    and parts[4] == "images"
                ):
                    asset_index = int(parts[3])

                    append_transfer_asset_image(
                        transfer_id=transfer_id,
                        transfer_created=transfer_created,
                        asset_index=asset_index,
                        file_data=file_data
                    )

            # ====================================================
            # Standalone asset images
            #
            # assets/{asset_index}/{filename}
            # ====================================================

            elif prefix == "assets":

                item_id = parts[1]

                append_file_to_table(
                    table=ASSETS_TABLE,
                    key={
                        "id": item_id
                    },
                    attribute_name="images",
                    file_data=file_data
                )

            else:

                print(
                    f"Unknown S3 prefix: {prefix}"
                )

        except Exception as exc:

            print(
                f"Error processing S3 record: {exc}"
            )

            # Re-raise so the S3/Lambda event source can retry
            # the failed record.
            raise

    return {
        "statusCode": 200,
        "message": "S3 records processed"
    }

# ---------------------------------------------------------------------------- #
#                                 OLD FUNCTION                                 #
# ---------------------------------------------------------------------------- #


# # $ This lambda function handles the file uploads to the s3 bucket and updates the dynamoDB images field

# import boto3
# from urllib.parse import unquote_plus
# from boto3.dynamodb.conditions import Key

# dynamodb = boto3.resource("dynamodb")

# MAINTENANCE_TABLE = dynamodb.Table("crud-nosql-app-maintenance-request-table")
# ASSETS_TABLE = dynamodb.Table("crud-nosql-app-assets-table")
# ACTION_TABLE = dynamodb.Table("crud-nosql-app-maintenance-action-table"
#                               )
# TRANSFER_TABLE = dynamodb.Table("crud-nosql-app-assets-transfer-table"
#                                 )


# def get_maintenance_sort_key(item_id: str):
#     response = MAINTENANCE_TABLE.query(
#         KeyConditionExpression=Key("id").eq(item_id),
#         Limit=1
#     )
#     items = response.get("Items", [])
#     if not items:
#         return None
#     return items[0].get("jobCreated")


# def get_action_sort_key(item_id: str):
#     response = ACTION_TABLE.query(
#         KeyConditionExpression=Key("id").eq(item_id),
#         Limit=1
#     )

#     items = response.get("Items", [])

#     if not items:
#         return None

#     return items[0].get("actionCreated")


# def get_transfers_sort_key(item_id: str):
#     response = TRANSFER_TABLE.query(
#         KeyConditionExpression=Key("transferId").eq(item_id),
#         Limit=1
#     )

#     items = response.get("Items", [])

#     if not items:
#         return None

#     return items[0].get("transferCreated")


# def append_file_to_table(
#     table,
#     key,
#     attribute_name,
#     file_data
# ):
#     table.update_item(
#         Key=key,
#         UpdateExpression=f"""
#             SET {attribute_name} = list_append(
#                 if_not_exists({attribute_name}, :empty),
#                 :file
#             )
#         """,
#         ExpressionAttributeValues={
#             ":file": [file_data],
#             ":empty": []
#         }
#     )


# def lambda_handler(event, context):
#     for record in event.get("Records", []):
#         bucket = record["s3"]["bucket"]["name"]
#         key = unquote_plus(record["s3"]["object"]["key"])

#         parts = key.split("/")

#         if len(parts) < 3:
#             continue

#         prefix = parts[0]
#         item_id = parts[1]
#         filename = parts[-1]

#         file_data = {
#             "bucket": bucket,
#             "key": key,
#             "filename": filename,
#         }

#         # =========================
#         # Maintenance request images
#         # =========================
#         if prefix == "maintenance":

#             job_created = get_maintenance_sort_key(item_id)

#             if not job_created:
#                 print(f"No maintenance item found for id={item_id}")
#                 continue

#             append_file_to_table(
#                 table=MAINTENANCE_TABLE,
#                 key={
#                     "id": item_id,
#                     "jobCreated": job_created
#                 },
#                 attribute_name="images",
#                 file_data=file_data
#             )

#         # =========================
#         # Maintenance action images
#         # =========================
#         elif prefix == "maintenance_action":

#             action_created = get_action_sort_key(item_id)

#             if not action_created:
#                 print(f"No action item found for id={item_id}")
#                 continue

#             append_file_to_table(
#                 table=ACTION_TABLE,
#                 key={
#                     "id": item_id,
#                     "actionCreated": action_created
#                 },
#                 attribute_name="images",
#                 file_data=file_data
#             )

#         # =========================
#         # Maintenance invoices
#         # =========================
#         elif prefix == "invoices":

#             action_created = get_action_sort_key(item_id)

#             if not action_created:
#                 print(f"No action item found for id={item_id}")
#                 continue

#             append_file_to_table(
#                 table=ACTION_TABLE,
#                 key={
#                     "id": item_id,
#                     "actionCreated": action_created
#                 },
#                 attribute_name="invoices",
#                 file_data=file_data
#             )

#         # =========================
#         # Transfer invoices
#         # =========================
#         elif prefix == "invoices":

#             transfer_created = get_transfers_sort_key(item_id)

#             if not transfer_created:
#                 print(f"No transfer item found for id={item_id}")
#                 continue

#             append_file_to_table(
#                 table=TRANSFER_TABLE,
#                 key={
#                     "transferId": item_id,
#                     "transferCreated": transfer_created
#                 },
#                 attribute_name="invoices",
#                 file_data=file_data
#             )

#         # =========================
#         # Asset images
#         # =========================
#         elif prefix == "assets":

#             append_file_to_table(
#                 table=ASSETS_TABLE,
#                 key={"id": item_id},
#                 attribute_name="images",
#                 file_data=file_data
#             )
