"""Retrieve a disposal request with formatted dates and asset download URLs."""

import json
import os

import boto3
from boto3.dynamodb.conditions import Key
from botocore.config import Config

from shared_utils._response import _response
from shared_utils.cors import handle_options_request, handle_request_metadata
from shared_utils.dynamodb import query_first
from shared_utils.to_human_date import format_dates


REGION = "af-south-1"
DISPOSAL_TABLE_NAME = "crud-nosql-app-assets-disposal-table"

dynamodb = boto3.resource("dynamodb", region_name=REGION)
disposal_table = dynamodb.Table(DISPOSAL_TABLE_NAME)
s3 = boto3.client(
    "s3",
    region_name=REGION,
    config=Config(
        s3={"addressing_style": "virtual"},
        signature_version="s3v4",
        region_name=REGION,
    ),
)
PRESIGN_EXPIRES_SECONDS = int(os.getenv("PRESIGN_EXPIRES_SECONDS", "900"))

STAGES = ("pending", "approved", "disposed", "cancelled", "rejected", "expired")
DATE_TIME_FIELDS = {"disposalCreated", "dateUpdated"}
DATE_FIELDS = {"expectedDisposalDate"}
ALLOWED_ORIGINS = [
    "https://www.crud-nosql.app.fabian-portfolio.net",
    "https://crud-nosql.app.fabian-portfolio.net",
    "http://localhost:5173",
    "http://localhost:8080",
]


def add_presigned_urls(data):
    """
    Recursively traverse dictionaries/lists and add presigned URLs
    to any object containing an S3 bucket/key pair.
    """

    # Handle dictionaries
    if isinstance(data, dict):

        # Detect S3 file object
        if "bucket" in data and "key" in data:
            bucket = data.get("bucket")
            key = data.get("key")

            new_data = {
                "key": key,
                "filename": data.get("filename")
                or (key.split("/")[-1] if key else None),
                "url": None,
            }

            if bucket and key:
                try:
                    new_data["url"] = s3.generate_presigned_url(
                        ClientMethod="get_object",
                        Params={
                            "Bucket": bucket,
                            "Key": key,
                        },
                        ExpiresIn=PRESIGN_EXPIRES_SECONDS,
                    )
                except Exception as e:
                    print("Presign error:", e)

            return new_data

        # Recursively process nested dict values
        return {
            k: add_presigned_urls(v)
            for k, v in data.items()
        }

    # Handle lists
    if isinstance(data, list):
        return [add_presigned_urls(item) for item in data]

    # Return primitive values unchanged
    return data


def build_disposal_response(item):
    """Build the detail response from the stages saved by postDisposalRequest."""
    response = {
        "id": item["disposalId"],
        "disposalCreated": item["disposalCreated"],
        "dateUpdated": item.get("dateUpdated"),
        "assets": item["assets"],
        "status": item["status"],
        "approvalReminderCount": item.get("approvalReminderCount", 0),
    }
    for stage in STAGES:
        response[stage] = item.get(stage)
    return response


def get_disposal_request(disposal_id, headers):
    """Query the disposal partition and return its saved request details."""
    item = query_first(
        disposal_table,
        KeyConditionExpression=Key("disposalId").eq(disposal_id),
    )
    if not item:
        return _response(404, {"message": "Disposal Request not found"}, headers)

    response = build_disposal_response(item)
    format_dates(
        response,
        date_time_fields=DATE_TIME_FIELDS,
        date_fields=DATE_FIELDS,
    )
    return _response(200, add_presigned_urls(response), headers)


def lambda_handler(event, context):
    print("event:", json.dumps(event))

    method, headers = handle_request_metadata(
        event,
        allowed_origins=ALLOWED_ORIGINS,
        allowed_methods="GET,OPTIONS",
    )
    options_response = handle_options_request(method, headers)
    if options_response:
        return options_response

    try:
        disposal_id = (event.get("pathParameters") or {}).get("id")
        if not disposal_id:
            return _response(400, {"message": "Missing disposal id"}, headers)

        return get_disposal_request(disposal_id, headers)
    except Exception as exc:
        print("Error retrieving disposal request:", repr(exc))
        return _response(500, {"message": "Internal server error"}, headers)
