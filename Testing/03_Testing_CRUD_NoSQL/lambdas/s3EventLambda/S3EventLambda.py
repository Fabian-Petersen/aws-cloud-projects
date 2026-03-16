# $ This lambda function handles the file uploads to the s3 bucket and updates the dynamoDB images field

import boto3
from urllib.parse import unquote_plus
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")

MAINTENANCE_TABLE = dynamodb.Table("crud-nosql-app-maintenance-request-table")
ASSETS_TABLE = dynamodb.Table("crud-nosql-app-assets-table")

def get_maintenance_sort_key(item_id: str):
    response = MAINTENANCE_TABLE.query(
        KeyConditionExpression=Key("id").eq(item_id),
        Limit=1
    )
    items = response.get("Items", [])
    if not items:
        return None
    return items[0].get("jobCreated")

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

        image_data = {
            "bucket": bucket,
            "key": key,
            "filename": filename,
        }

        if prefix == "maintenance":
            job_created = get_maintenance_sort_key(item_id)
            if not job_created:
                print(f"No maintenance item found for id={item_id}")
                continue

            MAINTENANCE_TABLE.update_item(
                Key={
                    "id": item_id,
                    "jobCreated": job_created
                },
                UpdateExpression="""
                    SET images = list_append(
                        if_not_exists(images, :empty),
                        :img
                    )
                """,
                ExpressionAttributeValues={
                    ":img": [image_data],
                    ":empty": []
                }
            )

        elif prefix == "assets":
            ASSETS_TABLE.update_item(
                Key={"id": item_id},
                UpdateExpression="""
                    SET images = list_append(
                        if_not_exists(images, :empty),
                        :img
                    )
                """,
                ExpressionAttributeValues={
                    ":img": [image_data],
                    ":empty": []
                }
            )