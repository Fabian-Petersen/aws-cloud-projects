Status = `Pending`

Investigate and fix the complete maintenance jobcard PDF generation lifecycle.

## Updated API route

The frontend now requests a jobcard using:

```text
GET /api/jobs/:id/jobcard
```

where:

```text
:id = action_id
```

So the download flow should now be treated as:

```text
Frontend
   ↓
GET /api/jobs/{action_id}/jobcard
   ↓
API Gateway
   ↓
getJobcardById
   ↓
use action_id to locate the related maintenance request
   ↓
determine expected jobcard PDF in S3
   ↓
return presigned URL
```

Verify the current API Gateway/Terraform configuration and frontend request implementation to confirm that this route is wired correctly.

Do not assume the path parameter represents the maintenance-request ID. It initially represents the maintenance action ID.

## Context

The intended workflow appears to be:

1. A maintenance request is approved.
2. `postApproveRequest` assigns a `jobcardNumber`.
3. A technician completes the job through `postJobAction`.
4. The maintenance action is created.
5. The related maintenance request is updated with:
   - `status = "complete"`
   - `action_id = <maintenance action id>`
6. The maintenance-request DynamoDB Stream invokes the container-based PDF Lambda stored in ECR.
7. The PDF Lambda retrieves:
   - the maintenance request;
   - the corresponding maintenance action;
   - generates a PDF;
   - stores it at something similar to:

```text
s3://crud-nosql-app-images/jobcards/{request_id}.pdf
```

8. Later, when the user selects **Download Jobcard**, the frontend calls:

```text
GET /api/jobs/{action_id}/jobcard
```

9. `getJobcardById` should retrieve the already-generated PDF and return a presigned S3 URL.

The download request should not normally generate the PDF.

At present, completed jobs do not have jobcard PDFs.

## Task

Trace the entire flow through the repository before changing anything.

Inspect at minimum:

- frontend jobcard download request
- API Gateway route for `/api/jobs/{id}/jobcard`
- `postApproveRequest`
- `postJobAction`
- `getJobcardById`
- PDF generator Lambda / `pdf_lambda`
- PDF Lambda Dockerfile
- Terraform for:
  - API Gateway
  - maintenance request table
  - maintenance action table
  - DynamoDB Streams
  - Lambda event source mappings
  - PDF Lambda
  - ECR image configuration
- `ActionIdIndex`
- maintenance request and maintenance action key schemas

## Verify `getJobcardById`

The route parameter is:

```text
action_id
```

Trace exactly how `getJobcardById` resolves this into the maintenance request.

The expected pattern is likely:

```text
action_id
   ↓
maintenance-request ActionIdIndex
   ↓
maintenance request
   ↓
request.id
   ↓
jobcards/{request.id}.pdf
```

Verify whether `ActionIdIndex` is actually configured as:

```text
PK = action_id
```

and whether the Lambda queries it correctly.

Do not confuse:

```text
API path id       = action_id
maintenance id    = request_id
PDF filename/key  = request_id
```

unless the actual repository currently implements something different.

If the implementation differs, document the actual relationship before changing it.

## Known / suspected problem 1: maintenance action lookup

The PDF Lambda reportedly performs something similar to:

```python
table_action.get_item(
    Key={"id": new_item["action_id"]}
)
```

Verify the current maintenance-action table key schema.

If it has a composite primary key such as:

```text
PK: id
SK: actionCreated
```

then `GetItem` with only `id` is invalid.

Fix the lookup appropriately.

Prefer querying by partition key `id` if that matches the current schema and access pattern.

Do not change the table schema unless necessary.

## Known / suspected problem 2: race condition

Check the exact order in `postJobAction`.

The suspected flow is:

```text
Update request to complete
        ↓
DynamoDB Stream fires
        ↓
PDF Lambda runs
        ↓
maintenance action is written afterwards
```

If this is still the current implementation, the PDF generator can execute before the action exists.

Correct the workflow.

The intended logical sequence should be:

```text
Create maintenance action
        ↓
Update maintenance request:
    action_id = action.id
    status = "complete"
        ↓
DynamoDB Stream fires
        ↓
PDF generator retrieves both records
        ↓
PDF generated
```

Where appropriate, use a DynamoDB transaction.

Also make the PDF consumer resilient if the action is temporarily unavailable.

Do not silently discard the stream event if the action cannot be retrieved.

## Known / suspected problem 3: status normalization

Verify the value actually written to the maintenance request.

The PDF generator reportedly checks:

```python
new_status == "complete"
```

Ensure the backend consistently stores:

```text
complete
```

rather than values such as:

```text
Complete
completed
COMPLETE
```

Normalize the backend value before writing it.

## Known / suspected problem 4: ECR image

Check the image version currently referenced by Terraform against:

- the latest PDF Lambda source;
- Dockerfile;
- build instructions;
- existing ECR tags.

There may be an old image such as `v2` deployed while newer source/build instructions refer to another tag.

Ensure the corrected PDF Lambda code is actually deployed.

Prefer an immutable tag or image digest.

## Stream handler requirements

Verify that the PDF Lambda:

- handles only relevant `MODIFY` events;
- detects an actual status transition;
- generates only when the new status becomes `complete`;
- ignores unrelated request modifications;
- logs failures clearly;
- is safe when multiple records arrive in one batch;
- does not permanently lose a PDF-generation event because one dependency was temporarily unavailable.

If appropriate, implement partial batch failure support using:

```python
batchItemFailures
```

and update the Lambda event source mapping accordingly.

## PDF idempotency

Before generating the PDF, check whether the expected S3 object already exists.

For example:

```text
jobcards/{request_id}.pdf
```

If it exists, do not unnecessarily regenerate it unless explicitly required.

This makes DynamoDB Stream retries safe.

## Existing completed jobs

Existing completed jobs have already transitioned to `complete`, so fixing the stream consumer will not automatically generate their missing PDFs.

Create a safe one-off backfill mechanism which:

1. identifies completed maintenance requests;
2. confirms `action_id` exists;
3. checks whether the expected PDF already exists;
4. retrieves the related maintenance action;
5. generates only missing PDFs.

Reuse the same PDF-generation code as the stream Lambda.

The backfill must be idempotent.

## Download behaviour

For:

```text
GET /api/jobs/{action_id}/jobcard
```

the Lambda should:

1. read `{action_id}` from the path;
2. locate the maintenance request through `ActionIdIndex`;
3. determine the request ID;
4. construct the expected PDF S3 key;
5. verify the object exists;
6. return a presigned download URL.

Conceptually:

```text
GET /api/jobs/abc123/jobcard

abc123
  ↓
ActionIdIndex
  ↓
request:
{
    id: "request-456",
    action_id: "abc123",
    status: "complete"
}
  ↓
jobcards/request-456.pdf
  ↓
presigned URL
```

If the PDF does not exist, return a meaningful API response rather than a broken URL, for example:

```json
{
  "success": false,
  "code": "JOBCARD_NOT_GENERATED",
  "message": "The jobcard PDF has not yet been generated."
}
```

Do not generate the PDF as a side effect of the download endpoint unless there is a compelling reason to redesign the architecture.

## Logging

Add useful logging around the lifecycle using values such as:

```text
request_id
action_id
jobcardNumber
old_status
new_status
pdf_s3_key
```

Useful stages include:

```text
JOB_COMPLETE_EVENT_RECEIVED
ACTION_LOOKUP_STARTED
ACTION_FOUND
PDF_GENERATION_STARTED
PDF_GENERATION_SUCCESS
PDF_ALREADY_EXISTS
PDF_GENERATION_FAILED
JOBCARD_DOWNLOAD_REQUESTED
JOBCARD_NOT_FOUND
JOBCARD_PRESIGNED_URL_CREATED
```

## Important constraints

- The current frontend route is `/api/jobs/:id/jobcard`.
- `:id` represents the `action_id`.
- Do not treat the route ID as the maintenance request ID.
- Do not change the frontend route unless there is a verified reason.
- Do not make jobcard creation dependent on the user clicking Download.
- Preserve the existing PDF design/layout.
- Preserve existing API contracts where possible.
- Avoid unnecessary DynamoDB scans in normal runtime paths.
- Do not modify unrelated maintenance functionality.

## Deliverables

After completing the investigation and fixes, provide:

1. The verified lifecycle from approval → completion → PDF generation → download.
2. The exact relationship between:
   - request ID
   - action ID
   - jobcard number
   - PDF S3 key
3. Root causes of the missing PDFs.
4. Files changed.
5. Code changes made.
6. Terraform changes made.
7. ECR rebuild/deployment steps.
8. Backfill approach for existing completed jobs.
9. Verification results.

Before modifying code, validate every assumption above against the current repository. If the repository differs, follow the actual implementation and explain the discrepancy.
