# This lambda function handles the file uploads to the s3 bucket and updates the dynamoDB images field

import boto3
from urllib.parse import unquote_plus

dynamodb = boto3.resource("dynamodb")

MAINTENANCE_TABLE = dynamodb.Table("crud-nosql-app-maintenance-request-table")
ASSETS_TABLE = dynamodb.Table("crud-nosql-app-assets-table")

def lambda_handler(event, context):
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])

        # Expected formats:
        # maintenance/{id}/{filename}
        # assets/{id}/{filename}
        parts = key.split("/")

        if len(parts) < 3:
            # Ignore unexpected paths
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
            table = MAINTENANCE_TABLE
        elif prefix == "assets":
            table = ASSETS_TABLE
        else:
            # Ignore other folders
            continue

        table.update_item(
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