"""Dry-run-first backfill for completed requests missing jobcard PDFs."""

import argparse
import json

import boto3
from boto3.dynamodb.conditions import Key

from lambda_handler import (
    BUCKET_NAME,
    JobcardDependencyUnavailable,
    generate_jobcard,
    get_action_by_id,
    jobcard_key,
    log_event,
    pdf_exists,
)


REGION = "af-south-1"
REQUEST_TABLE_NAME = "crud-nosql-app-maintenance-request-table"

dynamodb = boto3.resource("dynamodb", region_name=REGION)
request_table = dynamodb.Table(REQUEST_TABLE_NAME)


def iter_completed_requests():
    query = {
        "IndexName": "StatusIndex",
        "KeyConditionExpression": Key("status").eq("complete"),
    }

    while True:
        response = request_table.query(**query)
        yield from response.get("Items", [])

        last_evaluated_key = response.get("LastEvaluatedKey")
        if not last_evaluated_key:
            break
        query["ExclusiveStartKey"] = last_evaluated_key


def backfill(
    execute: bool = False,
    request_id: str | None = None,
    limit: int | None = None,
) -> dict:
    summary = {
        "mode": "execute" if execute else "dry-run",
        "completed_checked": 0,
        "already_exists": 0,
        "would_generate": 0,
        "generated": 0,
        "missing_action_id": 0,
        "missing_action": 0,
        "failed": 0,
    }

    for request_item in iter_completed_requests():
        current_request_id = str(request_item.get("id") or "").strip()
        if request_id and current_request_id != request_id:
            continue
        if limit is not None and summary["completed_checked"] >= limit:
            break

        summary["completed_checked"] += 1
        action_id = str(request_item.get("action_id") or "").strip()
        key = jobcard_key(current_request_id)

        try:
            if pdf_exists(key):
                summary["already_exists"] += 1
                log_event(
                    "PDF_ALREADY_EXISTS",
                    request_id=current_request_id,
                    action_id=action_id,
                    pdf_s3_key=key,
                    source="backfill",
                )
                continue

            if not action_id:
                summary["missing_action_id"] += 1
                log_event(
                    "PDF_GENERATION_FAILED",
                    request_id=current_request_id,
                    pdf_s3_key=key,
                    source="backfill",
                    error="Completed request is missing action_id",
                )
                continue

            action_item = get_action_by_id(action_id)
            if not action_item:
                summary["missing_action"] += 1
                log_event(
                    "PDF_GENERATION_FAILED",
                    request_id=current_request_id,
                    action_id=action_id,
                    pdf_s3_key=key,
                    source="backfill",
                    error="Linked action was not found",
                )
                continue

            if not execute:
                summary["would_generate"] += 1
                log_event(
                    "PDF_GENERATION_PLANNED",
                    request_id=current_request_id,
                    action_id=action_id,
                    jobcardNumber=request_item.get("jobcardNumber"),
                    pdf_s3_key=key,
                    source="backfill",
                )
                continue

            result = generate_jobcard(request_item, action_item=action_item)
            if result["status"] == "generated":
                summary["generated"] += 1
            else:
                summary["already_exists"] += 1

        except JobcardDependencyUnavailable as exc:
            summary["missing_action"] += 1
            log_event(
                "PDF_GENERATION_FAILED",
                request_id=current_request_id,
                action_id=action_id,
                pdf_s3_key=key,
                source="backfill",
                error=str(exc),
            )
        except Exception as exc:
            summary["failed"] += 1
            log_event(
                "PDF_GENERATION_FAILED",
                request_id=current_request_id,
                action_id=action_id,
                pdf_s3_key=key,
                source="backfill",
                error_type=type(exc).__name__,
                error=str(exc),
            )

    print(json.dumps({"stage": "BACKFILL_COMPLETE", **summary}))
    return summary


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate missing PDFs for completed maintenance requests."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Generate PDFs. Without this flag the command is a dry run.",
    )
    parser.add_argument(
        "--request-id",
        help="Restrict the backfill to one maintenance request ID.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of completed requests to inspect.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    backfill(
        execute=args.execute,
        request_id=args.request_id,
        limit=args.limit,
    )
