"""Delete a transfer request and every file stored beneath its S3 prefix."""

import boto3
import json
from boto3.dynamodb.conditions import Key

from shared_utils._response import _response
from shared_utils.cors import handle_options_request, handle_request_metadata
from shared_utils.dynamodb import query_first
from shared_utils.s3 import delete_prefix


REGION = "af-south-1"
TRANSFER_TABLE_NAME = "crud-nosql-app-assets-transfer-table"
BUCKET_NAME = "crud-nosql-app-images"

dynamodb = boto3.resource("dynamodb", region_name=REGION)
transfer_table = dynamodb.Table(TRANSFER_TABLE_NAME)
s3 = boto3.client("s3", region_name=REGION)


def lambda_handler(event, context):
    """Delete the transfer selected by the API's ``{id}`` path parameter."""
    print("event:", json.dumps(event))

    method, headers = handle_request_metadata(
        event,
        allowed_methods="DELETE,OPTIONS",
    )
    options_response = handle_options_request(method, headers)
    if options_response:
        return options_response

    try:
        transfer_id = (event.get("pathParameters") or {}).get("id")
        if not transfer_id:
            return _response(400, {"message": "Missing transfer id"}, headers)

        item = query_first(
            transfer_table,
            KeyConditionExpression=Key("transferId").eq(transfer_id),
            ProjectionExpression="transferId, transferCreated",
        )
        if not item:
            return _response(
                404,
                {"message": "Transfer Request not found"},
                headers,
            )

        prefix = f"transfers/{transfer_id}/"
        delete_prefix(s3, BUCKET_NAME, prefix)

        transfer_table.delete_item(
            Key={
                "transferId": transfer_id,
                "transferCreated": item["transferCreated"],
            }
        )

        return _response(
            200,
            {"message": "Transfer request and files deleted successfully"},
            headers,
        )
    except Exception as exc:
        print("Error deleting transfer request:", repr(exc))
        return _response(500, {"message": "Internal server error"}, headers)
