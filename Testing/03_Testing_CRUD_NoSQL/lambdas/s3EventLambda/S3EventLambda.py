# This lambda function handles the file uploads to the s3 bucket and updates the dynamoDB images field

import boto3
import os
from urllib.parse import unquote_plus

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("crud-nosql-app-maintenance-request-table")

def lambda_handler(event, context):
    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])

        # Extract maintenance ID from key
        # maintenance/{id}/{filename}
        parts = key.split("/")
        item_id = parts[1]
        filename = parts[-1]

        image_data = {
            "key": key,
            "filename": filename,
            "bucket": bucket
        }

        table.update_item(
            Key={"id": item_id},
            UpdateExpression="SET images = list_append(if_not_exists(images, :empty), :img)",
            ExpressionAttributeValues={
                ":img": [image_data],
                ":empty": []
            }
        )