from pdf_service.generator import PDFGenerator
import json

import boto3
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeDeserializer
from botocore.exceptions import ClientError


REGION = "af-south-1"
ACTION_TABLE_NAME = "crud-nosql-app-maintenance-action-table"
BUCKET_NAME = "crud-nosql-app-images"
MISSING_OBJECT_CODES = {"404", "NoSuchKey", "NotFound"}

deserializer = TypeDeserializer()
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table_action = dynamodb.Table(ACTION_TABLE_NAME)
s3 = boto3.client("s3", region_name=REGION)


class JobcardDependencyUnavailable(RuntimeError):
    """
    Raised when data required to generate a maintenance jobcard is not yet
    available.

    This is typically used when a completed maintenance request references an
    action that has either not been created yet or cannot be retrieved from the
    maintenance action table.

    Example:
        A maintenance request reaches status "complete" but does not yet contain
        an ``action_id``. Jobcard generation cannot continue because the PDF
        combines data from both the request and its corresponding action.
    """


def log_event(stage: str, **details) -> None:
    """
    Write a structured JSON log entry to standard output.

    Structured logs make it easier to search and filter Lambda logs in
    CloudWatch. The ``stage`` value identifies the processing step while
    additional keyword arguments provide contextual information such as request
    IDs, action IDs, jobcard numbers, or errors.

    Args:
        stage (str):
            Name of the processing stage or event being logged.

        **details:
            Additional key-value pairs to include in the JSON log entry.

    Returns:
        None

    Example:
        >>> log_event(
        ...     "PDF_GENERATION_STARTED",
        ...     request_id="abc-123",
        ...     action_id="action-456",
        ... )
        {"stage": "PDF_GENERATION_STARTED", "request_id": "abc-123",
         "action_id": "action-456"}
    """
    print(json.dumps({"stage": stage, **details}, default=str))


def ddb_to_dict(ddb_item: dict) -> dict:
    """
    Convert a raw DynamoDB Streams item into a standard Python dictionary.

    DynamoDB Streams represents attribute values using DynamoDB's typed JSON
    format, for example::

        {
            "id": {"S": "123"},
            "cost": {"N": "150.50"}
        }

    ``TypeDeserializer`` converts these values into normal Python values such
    as strings and ``Decimal`` objects.

    Args:
        ddb_item (dict):
            A DynamoDB item in DynamoDB Streams attribute-value format.

    Returns:
        dict:
            A dictionary containing deserialized Python values.

    Example:
        >>> ddb_to_dict({
        ...     "id": {"S": "REQ-001"},
        ...     "status": {"S": "complete"}
        ... })
        {
            "id": "REQ-001",
            "status": "complete"
        }
    """
    return {
        key: deserializer.deserialize(value)
        for key, value in ddb_item.items()
    }


def normalize_status(value) -> str:
    """
    Normalize a maintenance status value for reliable comparisons.

    The value is converted to a string, surrounding whitespace is removed, and
    the result is converted to lowercase.

    Args:
        value:
            Status value to normalize. This may be a string, ``None``, or
            another value that can be converted to a string.

    Returns:
        str:
            Normalized lowercase status string.

    Examples:
        >>> normalize_status("Complete")
        'complete'

        >>> normalize_status("  APPROVED  ")
        'approved'

        >>> normalize_status(None)
        ''
    """
    return str(value or "").strip().lower()


def jobcard_key(request_id: str) -> str:
    """
    Build the S3 object key used to store a generated jobcard PDF.

    Jobcards are stored inside the ``jobcards/`` prefix and use the maintenance
    request ID as the PDF filename.

    Args:
        request_id (str):
            Unique ID of the maintenance request.

    Returns:
        str:
            S3 object key for the jobcard PDF.

    Example:
        >>> jobcard_key("request-123")
        'jobcards/request-123.pdf'
    """
    return f"jobcards/{request_id}.pdf"


def pdf_exists(key: str) -> bool:
    """
    Check whether a jobcard PDF already exists in the configured S3 bucket.

    The function uses ``head_object`` so that the PDF contents do not need to be
    downloaded.

    Known missing-object errors such as ``404``, ``NoSuchKey``, and ``NotFound``
    are treated as a normal "file does not exist" result. Other S3 errors are
    re-raised so that unexpected failures are not silently ignored.

    Args:
        key (str):
            S3 object key to check.

    Returns:
        bool:
            ``True`` if the object exists, otherwise ``False``.

    Raises:
        ClientError:
            Re-raised when S3 returns an error other than one of the recognised
            missing-object responses.

    Example:
        >>> pdf_exists("jobcards/request-123.pdf")
        True
    """
    try:
        s3.head_object(Bucket=BUCKET_NAME, Key=key)
        return True
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code in MISSING_OBJECT_CODES:
            return False
        raise


def get_action_by_id(action_id: str) -> dict | None:
    """
    Retrieve the most recent maintenance action associated with an action ID.

    The maintenance action DynamoDB table is queried using ``id`` as the
    partition key. Results are returned in descending sort-key order and limited
    to one item, which means the most recent matching action is selected when
    multiple records exist.

    Args:
        action_id (str):
            Unique ID of the maintenance action to retrieve.

    Returns:
        dict | None:
            The matching maintenance action item if found, otherwise ``None``.

    Example:
        >>> action = get_action_by_id("action-123")
        >>> if action:
        ...     print(action["id"])
        action-123
    """
    log_event("ACTION_LOOKUP_STARTED", action_id=action_id)
    response = table_action.query(
        KeyConditionExpression=Key("id").eq(action_id),
        ScanIndexForward=False,
        Limit=1,
    )
    items = response.get("Items", [])
    if not items:
        return None

    action_item = items[0]
    log_event(
        "ACTION_FOUND",
        action_id=action_id,
        action_created=action_item.get("actionCreated"),
    )
    return action_item


def build_jobcard_data(request_item: dict, action_item: dict) -> dict:
    """
    Combine maintenance request and maintenance action data into the structure
    expected by the PDF generator.

    The request and action both contain an ``id`` field, so these values are
    renamed before the dictionaries are merged:

    - request ``id`` becomes ``request_id``
    - action ``id`` becomes ``action_id``

    The action data is then merged over the request data.

    The existing PDF layout expects top-level ``equipment`` and ``assetID``
    fields. Newer maintenance requests may instead contain multiple assets
    inside an ``assets`` list. When the legacy top-level fields are absent,
    this function derives comma-separated equipment names and asset IDs from
    that list.

    Args:
        request_item (dict):
            Maintenance request record from DynamoDB.

        action_item (dict):
            Maintenance action record associated with the request.

    Returns:
        dict:
            Combined and normalized jobcard data ready to be passed to
            ``PDFGenerator.create_pdf``.

    Example:
        Given a request containing::

            {
                "id": "request-1",
                "assets": [
                    {
                        "assetID": "A001",
                        "equipment": "Bandsaw"
                    },
                    {
                        "assetID": "A002",
                        "equipment": "Mincer"
                    }
                ]
            }

        the returned jobcard data will contain::

            {
                "request_id": "request-1",
                "equipment": "Bandsaw, Mincer",
                "assetID": "A001, A002",
                ...
            }
    """
    request_copy = request_item.copy()
    action_copy = action_item.copy()

    request_copy["request_id"] = request_copy.pop("id")
    action_copy["action_id"] = action_copy.pop("id")

    jobcard_data = {**request_copy, **action_copy}

    # Current requests may contain multiple assets instead of the legacy
    # top-level equipment/assetID fields expected by the existing PDF layout.
    assets = request_item.get("assets") or []
    if not jobcard_data.get("equipment") and assets:
        equipment = [
            str(asset.get("equipment") or "").strip()
            for asset in assets
            if str(asset.get("equipment") or "").strip()
        ]
        jobcard_data["equipment"] = ", ".join(equipment)

    if not jobcard_data.get("assetID") and assets:
        asset_ids = [
            str(asset.get("assetID") or "").strip()
            for asset in assets
            if str(asset.get("assetID") or "").strip()
        ]
        jobcard_data["assetID"] = ", ".join(asset_ids)

    jobcard_data.setdefault("equipment", "")
    jobcard_data.setdefault("assetID", "")
    return jobcard_data


def generate_jobcard(
    request_item: dict,
    action_item: dict | None = None,
) -> dict:
    """
    Generate and store a completed maintenance request's jobcard PDF.

    This function coordinates the complete jobcard-generation process:

    1. Extract the maintenance request ID and action ID.
    2. Validate that both required identifiers are available.
    3. Build the expected S3 jobcard key.
    4. Check whether the PDF already exists.
    5. Retrieve the associated maintenance action when one was not supplied.
    6. Combine request and action data.
    7. Generate the PDF using ``PDFGenerator``.
    8. Upload the resulting PDF to S3.

    Existing PDFs are not regenerated. This makes the operation effectively
    idempotent for a request whose PDF has already been stored.

    Args:
        request_item (dict):
            Completed maintenance request containing at minimum an ``id`` and
            ``action_id``.

        action_item (dict | None, optional):
            Corresponding maintenance action. If omitted, the action is looked
            up from DynamoDB using the request's ``action_id``.

    Returns:
        dict:
            A result describing whether the PDF was generated or already
            existed.

            Example generated result::

                {
                    "status": "generated",
                    "key": "jobcards/request-123.pdf"
                }

            Example existing result::

                {
                    "status": "already_exists",
                    "key": "jobcards/request-123.pdf"
                }

    Raises:
        ValueError:
            If the completed request does not contain an ``id``.

        JobcardDependencyUnavailable:
            If the request does not contain an ``action_id`` or the referenced
            maintenance action cannot be found.

        ClientError:
            If an unexpected S3 or DynamoDB client error occurs.

    Example:
        >>> result = generate_jobcard({
        ...     "id": "request-123",
        ...     "action_id": "action-456",
        ...     "status": "complete",
        ...     "jobcardNumber": "Job-PLP-202610-0001"
        ... })
        >>> result["status"]
        'generated'
    """
    request_id = str(request_item.get("id") or "").strip()
    action_id = str(request_item.get("action_id") or "").strip()
    jobcard_number = request_item.get("jobcardNumber", "")

    if not request_id:
        raise ValueError("Completed request is missing id")
    if not action_id:
        raise JobcardDependencyUnavailable(
            f"Completed request {request_id} is missing action_id"
        )

    key = jobcard_key(request_id)
    if pdf_exists(key):
        log_event(
            "PDF_ALREADY_EXISTS",
            request_id=request_id,
            action_id=action_id,
            jobcardNumber=jobcard_number,
            pdf_s3_key=key,
        )
        return {"status": "already_exists", "key": key}

    if action_item is None:
        action_item = get_action_by_id(action_id)

    if not action_item:
        raise JobcardDependencyUnavailable(
            f"Action {action_id} is not available for request {request_id}"
        )

    jobcard_data = build_jobcard_data(request_item, action_item)
    log_event(
        "PDF_GENERATION_STARTED",
        request_id=request_id,
        action_id=action_id,
        jobcardNumber=jobcard_number,
        pdf_s3_key=key,
    )

    pdf_bytes = PDFGenerator().create_pdf(jobcard_data)
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=key,
        Body=pdf_bytes,
        ContentType="application/pdf",
    )

    log_event(
        "PDF_GENERATION_SUCCESS",
        request_id=request_id,
        action_id=action_id,
        jobcardNumber=jobcard_number,
        pdf_s3_key=key,
        pdf_size=len(pdf_bytes),
    )
    return {"status": "generated", "key": key}


def process_stream_record(record: dict) -> dict:
    """
    Process one DynamoDB Streams record and generate a jobcard when a request
    transitions to ``complete``.

    Only ``MODIFY`` stream events are relevant. INSERT and REMOVE events are
    ignored.

    The function compares the old and new maintenance request statuses. A PDF
    is generated only when:

    - the status has changed, and
    - the new normalized status is ``complete``.

    For example, the following transition triggers generation::

        approved -> complete

    The following transitions are ignored::

        complete -> complete
        pending -> approved
        INSERT event

    Args:
        record (dict):
            A single DynamoDB Streams event record.

    Returns:
        dict:
            Processing result.

            Ignored records return::

                {"status": "ignored"}

            A qualifying completion event returns the result from
            ``generate_jobcard``.

    Raises:
        Exception:
            Exceptions raised during jobcard generation are intentionally not
            handled here. They propagate to ``lambda_handler``, which records
            the failed stream item for retry.

    Example:
        A stream record where::

            OldImage.status = "approved"
            NewImage.status = "complete"

        causes ``generate_jobcard`` to be called using the new DynamoDB item.
    """
    if record.get("eventName") != "MODIFY":
        return {"status": "ignored"}

    dynamodb_record = record.get("dynamodb") or {}
    old = dynamodb_record.get("OldImage")
    new = dynamodb_record.get("NewImage")
    if not old or not new:
        return {"status": "ignored"}

    old_item = ddb_to_dict(old)
    new_item = ddb_to_dict(new)
    old_status = normalize_status(old_item.get("status"))
    new_status = normalize_status(new_item.get("status"))

    if old_status == new_status or new_status != "complete":
        return {"status": "ignored"}

    log_event(
        "JOB_COMPLETE_EVENT_RECEIVED",
        request_id=new_item.get("id"),
        action_id=new_item.get("action_id"),
        jobcardNumber=new_item.get("jobcardNumber"),
        old_status=old_status,
        new_status=new_status,
        pdf_s3_key=jobcard_key(new_item.get("id")),
    )
    return generate_jobcard(new_item)


def record_identifier(record: dict, index: int) -> str:
    """
    Determine the identifier used to report a failed DynamoDB Streams record.

    The function attempts to use the most specific identifier available in the
    following order:

    1. DynamoDB stream ``SequenceNumber``
    2. Lambda event ``eventID``
    3. A generated fallback based on the record's batch index

    This identifier is returned through Lambda's partial batch response so that
    failed records can be retried without retrying successfully processed
    records.

    Args:
        record (dict):
            DynamoDB Streams Lambda event record.

        index (int):
            Position of the record within the current Lambda event batch.

    Returns:
        str:
            Identifier to use in ``batchItemFailures``.

    Examples:
        If a sequence number exists::

            '496645321123456789'

        If no sequence number or event ID exists::

            'record-2'
    """
    dynamodb_record = record.get("dynamodb") or {}
    return str(
        dynamodb_record.get("SequenceNumber")
        or record.get("eventID")
        or f"record-{index}"
    )


def lambda_handler(event, context):
    """
    AWS Lambda entry point for processing maintenance-request DynamoDB Stream
    events.

    The Lambda processes every record in the incoming batch independently.

    Records that do not represent a transition to ``complete`` are ignored.
    Records that successfully trigger jobcard generation complete normally.

    If processing a record raises an exception, its identifier is added to the
    ``batchItemFailures`` response. This supports Lambda's partial batch failure
    handling for DynamoDB Streams, allowing only failed records to be retried
    instead of replaying the entire batch.

    Args:
        event (dict):
            AWS Lambda event containing DynamoDB Streams records under the
            ``Records`` key.

        context:
            AWS Lambda runtime context object. The current implementation does
            not use it directly.

    Returns:
        dict:
            Partial batch response containing any failed record identifiers.

            Successful batch example::

                {
                    "batchItemFailures": []
                }

            Batch with one failed record example::

                {
                    "batchItemFailures": [
                        {
                            "itemIdentifier": "496645321123456789"
                        }
                    ]
                }

    Example:
        >>> event = {
        ...     "Records": [
        ...         {
        ...             "eventName": "MODIFY",
        ...             "dynamodb": {
        ...                 "SequenceNumber": "12345",
        ...                 "OldImage": {...},
        ...                 "NewImage": {...}
        ...             }
        ...         }
        ...     ]
        ... }
        >>> lambda_handler(event, None)
        {"batchItemFailures": []}
    """
    print("event:", json.dumps(event))
    batch_item_failures = []

    for index, record in enumerate(event.get("Records", [])):
        try:
            process_stream_record(record)
        except Exception as exc:
            identifier = record_identifier(record, index)
            log_event(
                "PDF_GENERATION_FAILED",
                item_identifier=identifier,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            batch_item_failures.append({"itemIdentifier": identifier})

    return {"batchItemFailures": batch_item_failures}


if __name__ == "__main__":
    with open("event.json", encoding="utf-8") as event_file:
        print(json.dumps(lambda_handler(json.load(event_file), None), indent=2))
