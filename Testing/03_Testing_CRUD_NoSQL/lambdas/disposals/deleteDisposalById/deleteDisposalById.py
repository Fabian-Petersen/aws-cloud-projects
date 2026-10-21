"""Delete a disposal request and every file stored beneath its S3 prefix."""

import boto3
import json
from boto3.dynamodb.conditions import Key

from shared_utils._response import _response
from shared_utils.cors import handle_options_request, handle_request_metadata
from shared_utils.dynamodb import query_first
from shared_utils.s3 import delete_prefix


REGION = "af-south-1"
DISPOSAL_TABLE_NAME = "crud-nosql-app-assets-disposal-table"
BUCKET_NAME = "crud-nosql-app-images"

dynamodb = boto3.resource("dynamodb", region_name=REGION)
disposal_table = dynamodb.Table(DISPOSAL_TABLE_NAME)
s3 = boto3.client("s3", region_name=REGION)


def lambda_handler(event, context):
    """Delete the disposal selected by the API's ``{id}`` path parameter."""
    print("event:", json.dumps(event))

    method, headers = handle_request_metadata(
        event,
        allowed_methods="DELETE,OPTIONS",
    )
    options_response = handle_options_request(method, headers)
    if options_response:
        return options_response

    try:
        disposal_id = (event.get("pathParameters") or {}).get("id")
        if not disposal_id:
            return _response(400, {"message": "Missing disposal id"}, headers)

        item = query_first(
            disposal_table,
            KeyConditionExpression=Key("disposalId").eq(disposal_id),
            ProjectionExpression="disposalId, disposalCreated",
        )
        if not item:
            return _response(
                404,
                {"message": "Disposal Request not found"},
                headers,
            )

        prefix = f"disposals/{disposal_id}/"
        delete_prefix(s3, BUCKET_NAME, prefix)

        disposal_table.delete_item(
            Key={
                "disposalId": disposal_id,
                "disposalCreated": item["disposalCreated"],
            }
        )

        return _response(
            200,
            {"message": "Disposal request and files deleted successfully"},
            headers,
        )
    except Exception as exc:
        print("Error deleting disposal request:", repr(exc))
        return _response(500, {"message": "Internal server error"}, headers)
