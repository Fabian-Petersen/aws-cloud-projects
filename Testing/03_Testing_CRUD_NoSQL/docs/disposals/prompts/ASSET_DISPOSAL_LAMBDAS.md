# Codex Task — Asset Disposals Backend

## Task 1 — Implement `postDisposalRequest`

The AWS infrastructure required for the Asset Disposal feature has already been created manually.

Do **not** create, redesign, or modify infrastructure resources unless an existing configuration must be inspected to determine how the Lambda is invoked.

This task is focused on implementing the Python code for:

```text
postDisposalRequest
```

which handles:

```text
POST /api/disposals
```

Use:

```text
README_ASSET_DISPOSAL.md
```

as the functional/business-logic reference.

Also inspect the existing **Asset Transfer** backend implementation, particularly the Lambda responsible for creating a transfer request, because the disposal workflow follows many of the same backend patterns.

---

# Important — Infrastructure Already Exists

The following resources have already been created.

Do not recreate them:

```text
DynamoDB disposal table
API Gateway disposal routes
Lambda resources
IAM permissions
environment variables
S3 infrastructure
EventBridge infrastructure
Scheduler infrastructure
Cognito authorizer
```

Do not modify Terraform merely to recreate resources that already exist.

You may inspect Terraform/tfvars to determine:

```text
Lambda environment variable names
DynamoDB table names
S3 bucket configuration
Scheduler configuration
API route mapping
existing Lambda packaging conventions
```

but this task is primarily a Python Lambda implementation task.

---

# Shared Utilities

A shared helper implementation now exists under:

```text
/layers/python/shared_utils
```

This contains the common Lambda helper functionality used by the backend, including helpers for functionality such as:

```text
Decimal serialization
HTTP responses
CORS headers
Cognito claims

date/time handling
common validation
other reusable Lambda utilities
```

## Important Packaging Rule

We are **not using a Lambda Layer to deploy these shared utilities**.

Instead, the shared source must be injected/copied into each Lambda deployment ZIP during packaging.

The source of truth must remain:

```text
/layers/python/shared_utils
```

Do not copy and maintain separate versions of these helpers inside individual Lambda source directories.

Do not recreate functions locally when they already exist in `shared_utils`.

The deployment ZIP should contain the shared module alongside the Lambda code so that imports work at runtime.

For example, depending on the actual repository structure, the final ZIP should conceptually resemble:

```text
lambda_function.py
shared_utils/
    __init__.py
    ...
```

or, if `shared_utils` is implemented as one Python module:

```text
lambda_function.py
shared_utils.py
```

Inspect the existing `/layers/python/shared_utils` structure and use the correct form.

The important requirement is:

```text
/layers/python/shared_utils
        ↓ packaging
Lambda ZIP
        ↓
import shared_utils
```

A change made to the source under:

```text
/layers/python/shared_utils
```

must therefore be included automatically whenever dependent Lambdas are rebuilt.

Do not create a separate physical copy in every Lambda source folder.

---

# Reference Existing Lambdas

Before implementing `postDisposalRequest`, inspect relevant existing Lambdas, particularly the transfer request Lambda.

Reuse existing implementation patterns for:

```text
event parsing
Cognito claims
responses
CORS
exceptions
DynamoDB access
asset lookup
S3 presigned URLs
UUID generation
date/time generation
scheduler handling
environment variables
logging
```

Do not unnecessarily refactor existing transfer code.

Do not change unrelated Lambdas.

---

# Lambda Responsibility

Implement:

```text
postDisposalRequest
```

for:

```text
POST /api/disposals
```

The Lambda creates a new disposal request.

It must:

```text
Receive frontend payload
        ↓
Validate payload
        ↓
Validate / enrich assets
        ↓
Generate disposalId
        ↓
Generate disposalCreated
        ↓
Read Cognito requestor identity
        ↓
Build assets[]
        ↓
Generate S3 presigned URLs where required
        ↓
Create PENDING disposal record
        ↓
Create approval timeout schedule if existing configuration supports it
        ↓
Return disposal record + presigned URLs
```

Creating a disposal request must **not** dispose of an asset.

---

# DynamoDB Key

The disposal table uses:

```text
PK: disposalId
SK: disposalCreated
```

Where:

```text
disposalId
```

is a backend-generated UUID.

And:

```text
disposalCreated
```

is a backend-generated ISO-8601 timestamp.

Example:

```text
disposalId:
535be3f9-b1c1-4d35-8836-36c3b8d6c69d

disposalCreated:
2026-09-04T11:00:00.000000+02:00
```

Do not accept either value from the frontend.

---

# Initial Status

Every new disposal request must initially use:

```text
pending
```

Follow the application's existing lowercase backend status convention.

Do not use:

```text
PENDING
```

if the current backend convention is lowercase.

---

# Frontend Request

The frontend sends disposal information containing one or more assets.

The Lambda must support both:

```text
identified assets
```

and:

```text
unidentified assets
```

An identified asset contains an `assetID`.

An unidentified asset does not have an `assetID` and relies on the descriptive information supplied by the user.

A representative payload is:

```json
{
  "location": "Maitland",
  "expectedDisposalDate": "2026-09-30",
  "disposalReason": "Beyond economical repair",
  "description": "Assets are no longer economical to maintain.",
  "assets": [
    {
      "assetIndex": 0,
      "assetID": "RT-0013",
      "area": "Processing",
      "equipment": "Biltong Maker",
      "assetIssueReason": "beyond_economical_repair",
      "assetIssueDetails": "",
      "images": [
        {
          "filename": "asset.webp",
          "content_type": "image/webp"
        }
      ]
    },
    {
      "assetIndex": 1,
      "area": "Storage",
      "equipment": "Unknown Freezer",
      "assetIssueReason": "obsolete",
      "assetIssueDetails": "Asset identification plate is missing.",
      "images": []
    }
  ]
}
```

Use the actual frontend schema and current frontend implementation as the final authority for exact property names if it differs slightly from this example.

Do not change frontend files in this task.

---

# Required Request Fields

Validate the request according to the frontend contract and existing backend conventions.

At minimum the request should contain:

```text
location
expectedDisposalDate
disposalReason
assets
```

`assets` must contain at least one asset.

`description` may follow the optional/required behaviour defined by the frontend schema.

Do not silently accept malformed payloads.

---

# Identified Assets

An asset is identified when:

```text
assetID
```

contains a value.

Example:

```json
{
  "assetIndex": 0,
  "assetID": "RT-0013"
}
```

For identified assets:

1. Retrieve the authoritative asset record from the existing assets DynamoDB table.
2. Use the same `assetID` lookup pattern currently used elsewhere in the application.
3. If the asset does not exist, reject the complete disposal request.
4. Do not trust client-supplied authoritative asset information when the asset exists in the asset registry.
5. Use the database asset record to populate values such as:

```text
assetID
equipment
area
location where applicable
```

6. Preserve disposal-specific information supplied by the frontend:

```text
assetIssueReason
assetIssueDetails
image metadata
assetIndex
```

The request must not partially succeed when one identified asset cannot be resolved.

---

# Unidentified Assets

The disposal workflow also supports assets that cannot be matched to an asset registry record.

An asset is considered unidentified when:

```text
assetID
```

is absent, empty, or otherwise not supplied according to the frontend schema.

For an unidentified asset:

Do **not** perform an assets table lookup.

Use the frontend-provided values:

```text
area
equipment
assetIssueReason
assetIssueDetails
images
assetIndex
```

The resulting disposal asset should remain clearly distinguishable from an identified registered asset because it will have no `assetID`.

Do not generate a fake asset ID.

Do not insert an unidentified asset into `assets_table`.

Asset creation is outside the responsibility of this Lambda.

---

# Duplicate Asset Validation

Prevent duplicate identified assets within one disposal request.

For example:

```json
{
  "assets": [
    {
      "assetID": "RT-0013"
    },
    {
      "assetID": "RT-0013"
    }
  ]
}
```

must fail validation.

Only non-empty `assetID` values participate in duplicate-ID checking.

Two unidentified assets must not automatically be considered duplicates merely because they both have no asset ID.

---

# Asset Eligibility

If the repository already defines which registered asset statuses can be included in a disposal request, enforce those rules.

Do not invent new status values.

If disposal eligibility has not yet been formally implemented, isolate the validation so it can be added later without restructuring the Lambda.

Document this as an assumption in the final Codex summary.

---

# Requestor Identity

Do not trust requestor identity sent by the frontend.

Use authenticated Cognito claims.

Use the existing helper from:

```text
shared_utils
```

for extracting claims if one already exists.

Populate the same identity fields used by the rest of the application.

Expected fields include:

```text
requestorSub
requestorEmail
requestedBy
requestorName
```

Use the actual Cognito claim mappings already established in the backend.

Do not introduce a new claim interpretation just for disposals.

---

# Backend-Generated Values

Generate:

```text
disposalId
disposalCreated
status
requestorSub
requestorEmail
requestedBy
requestorName
approvalReminderCount
schedule_name
```

in the backend.

Expected values:

```text
disposalId
    UUID

disposalCreated
    current backend ISO-8601 timestamp

status
    pending

approvalReminderCount
    0

schedule_name
    disposal-{disposalId}-timeout
```

Use the relevant functions from:

```text
shared_utils
```

rather than recreating common functionality locally.

---

# Asset Structure Stored in DynamoDB

Build one `assets[]` array inside the disposal request.

Example identified asset:

```json
{
  "assetIndex": 0,
  "assetID": "RT-0013",
  "equipment": "Biltong Maker",
  "area": "processing",
  "assetIssueReason": "beyond_economical_repair",
  "assetIssueDetails": "",
  "images": []
}
```

Example unidentified asset:

```json
{
  "assetIndex": 1,
  "equipment": "Unknown Freezer",
  "area": "storage",
  "assetIssueReason": "obsolete",
  "assetIssueDetails": "Asset identification plate is missing.",
  "images": []
}
```

Do not create a separate DynamoDB disposal item for each asset.

The entire disposal request must be one item.

---

# Progressive Disposal Record

Create the initial DynamoDB item using the progressive-enrichment structure defined by the disposal feature.

Conceptually:

```json
{
  "disposalId": "535be3f9-b1c1-4d35-8836-36c3b8d6c69d",
  "disposalCreated": "2026-09-04T11:00:00.000000+02:00",
  "status": "pending",

  "requestorSub": "cognito-sub",
  "requestorEmail": "user@example.com",
  "requestedBy": "Full Name",
  "requestorName": "First Name",

  "location": "Maitland",
  "expectedDisposalDate": "2026-09-30",
  "disposalReason": "Beyond economical repair",
  "description": "Assets are no longer economical to maintain.",

  "approvalReminderCount": 0,
  "schedule_name": "disposal-535be3f9-b1c1-4d35-8836-36c3b8d6c69d-timeout",

  "assets": [
    {
      "assetIndex": 0,
      "assetID": "RT-0013",
      "equipment": "Biltong Maker",
      "area": "processing",
      "assetIssueReason": "beyond_economical_repair",
      "assetIssueDetails": "",
      "images": []
    }
  ],

  "pending": {
    "requestedBy": "Full Name",
    "requestorName": "First Name",
    "requestorSub": "cognito-sub",
    "description": "Assets are no longer economical to maintain.",
    "disposalReason": "Beyond economical repair",
    "location": "Maitland",
    "expectedDisposalDate": "2026-09-30"
  },

  "approved": null,
  "disposed": null,
  "cancelled": null,
  "rejected": null,
  "expired": null
}
```

Use actual repository naming conventions where an established convention differs.

The important architectural rule is that later Lambdas enrich this same item rather than creating separate workflow records.

---

# Asset Images

Images belong to individual entries in:

```text
assets[]
```

The frontend sends file metadata rather than file contents.

Example:

```json
{
  "filename": "asset.webp",
  "content_type": "image/webp"
}
```

Generate S3 PUT presigned URLs using the existing transfer implementation as the reference.

Use the existing S3 client/configuration and existing helper functions wherever possible.

Use a key structure consistent with the disposal specification:

```text
disposals/{disposalId}/assets/{assetIndex}/images/{filename}
```

For example:

```text
disposals/535be3f9-b1c1-4d35-8836-36c3b8d6c69d/assets/0/images/asset.webp
```

---

# Presigned URL Response

Return sufficient metadata for the frontend to map every generated URL back to the correct asset.

Each image response should contain the equivalent of:

```json
{
  "type": "images",
  "assetIndex": 0,
  "assetID": "RT-0013",
  "filename": "asset.webp",
  "url": "https://...",
  "key": "disposals/.../assets/0/images/asset.webp",
  "content_type": "image/webp"
}
```

For unidentified assets:

```text
assetID
```

may be omitted or null according to the existing API serialization convention.

`assetIndex` must still be returned.

Do not use `assetID` as the only method for associating an uploaded image with an asset because unidentified assets do not have one.

---

# Content-Type Requirement

When generating the presigned PUT URL, include:

```text
ContentType
```

using the frontend-supplied:

```text
content_type
```

The value returned in the presigned URL metadata must match the value the frontend uses during the S3 PUT request.

Follow the same implementation that has already been proven to work for transfer image uploads.

---

# Initial Images Value

When initially writing the DynamoDB disposal request, each asset must contain:

```json
{
  "images": []
}
```

Do not store temporary presigned URLs in DynamoDB.

Presigned URLs are temporary API response data.

The existing S3 upload-processing mechanism can update permanent image metadata after successful S3 upload if that mechanism supports disposals.

Do not duplicate the existing generic S3 event-processing Lambda unnecessarily.

---

# Approval Scheduler

Inspect the existing transfer request Lambda and existing disposal environment variables.

If the manually-created infrastructure already provides everything required for the disposal request Lambda to create the approval timeout schedule, use the same scheduler pattern as transfers.

Expected schedule name:

```text
disposal-{disposalId}-timeout
```

Store this value in:

```text
schedule_name
```

Do not create Scheduler infrastructure.

Do not create a scheduler role.

Do not create the timeout Lambda.

Only invoke existing configured infrastructure if it is already ready for use.

If the timeout target has not yet been implemented or configured, keep the generated `schedule_name` in the record but do not create an invalid Scheduler target.

Document this in the final summary.

---

# DynamoDB Write

Perform validation before writing the disposal item.

The required order should be approximately:

```text
Parse request
        ↓
Validate required fields
        ↓
Validate asset array
        ↓
Detect duplicate asset IDs
        ↓
Retrieve all identified asset records
        ↓
Validate asset eligibility
        ↓
Build normalized assets[]
        ↓
Generate request metadata
        ↓
Generate presigned URLs
        ↓
Create DynamoDB item
        ↓
Create Scheduler schedule if supported
        ↓
Return response
```

Do not write a partial disposal item before asset validation has succeeded.

Use the existing DynamoDB client/resource pattern used by the repository.

---

# Do Not Modify `assets_table`

`postDisposalRequest` is not allowed to modify asset records.

It may read:

```text
assets_table
```

to validate and enrich identified assets.

It must not:

```text
change asset status
mark asset disposed
change location
delete asset
create asset
update equipment
update area
```

Asset modification occurs only when the future disposal-completion Lambda performs:

```text
approved → disposed
```

---

# Response

Return the created disposal request and generated presigned URLs using the application's established response format.

Conceptually:

```json
{
  "data": {
    "disposalId": "535be3f9-b1c1-4d35-8836-36c3b8d6c69d",
    "disposalCreated": "2026-09-04T11:00:00.000000+02:00",
    "status": "pending",
    "location": "Maitland",
    "expectedDisposalDate": "2026-09-30",
    "disposalReason": "Beyond economical repair",
    "description": "Assets are no longer economical to maintain.",
    "requestorSub": "...",
    "requestorEmail": "...",
    "requestedBy": "...",
    "requestorName": "...",
    "approvalReminderCount": 0,
    "schedule_name": "disposal-...-timeout",
    "assets": []
  },
  "presigned_urls": [
    {
      "type": "images",
      "assetIndex": 0,
      "assetID": "RT-0013",
      "filename": "asset.webp",
      "content_type": "image/webp",
      "key": "disposals/.../assets/0/images/asset.webp",
      "url": "..."
    }
  ]
}
```

Return the complete normalized `assets[]` data in the actual response.

The abbreviated empty array above is only illustrative.

Use the existing response helper from:

```text
shared_utils
```

rather than manually rebuilding the application's API response format.

---

# Error Handling

Use the shared response/error helpers and existing application conventions.

Handle at minimum:

```text
400
Malformed request body

400
Missing required fields

400
No assets supplied

400
Duplicate identified assetID

404
Identified asset does not exist

409
Registered asset is not eligible for disposal
if eligibility rules currently exist

500
Unexpected backend error
```

Do not expose internal stack traces to the API client.

Log sufficient context to CloudWatch using the repository's existing conventions.

---

# CORS

Do not manually duplicate CORS constants if they exist in:

```text
shared_utils
```

Use the shared implementation.

Follow the same OPTIONS/API Gateway assumptions currently used by the other backend Lambdas.

---

# Decimal Serialization

If DynamoDB values contain:

```text
Decimal
```

use the implementation already available in:

```text
shared_utils
```

Do not create another decimal serializer inside `postDisposalRequest`.

---

# Date Helpers

Use the common date helper from:

```text
shared_utils
```

for generating:

```text
disposalCreated
```

The DynamoDB source value must remain an ISO timestamp.

Example:

```text
2026-09-04T11:00:00.000000+02:00
```

Do not store:

```text
04 Sep 2026, 11:00
```

as the source database timestamp.

Formatting for display belongs in GET responses/frontend presentation where applicable.

---

# Lambda Packaging

Inspect the existing Lambda ZIP packaging implementation.

Update the packaging mechanism so `postDisposalRequest` receives the shared helper source from:

```text
/layers/python/shared_utils
```

The shared code must be injected during build/package creation.

Do not manually paste the shared utility source into the Lambda directory.

A rebuild should conceptually perform:

```text
postDisposalRequest source
        +
/layers/python/shared_utils
        ↓
deployment ZIP
```

This pattern will later be used by every Lambda that consumes the common helpers.

The goal is:

```text
update shared_utils once
        ↓
rebuild Lambdas
        ↓
all dependent Lambda ZIPs contain the updated version
```

Do not create or attach a Lambda Layer for this purpose.

---

# Scope Restrictions

For this task, implement only:

```text
postDisposalRequest
```

Do not implement:

```text
getDisposalList
getDisposalById
getMyDisposals
postDisposalApproval
postDisposalRejection
postDisposalCancel
postDisposal
checkDisposalApprovalTimeout
handleDisposalNotifications
assetDisposalRequest
assetDisposalApproval
assetDisposalComplete
```

Do not create new AWS resources.

Do not change frontend code.

Do not change transfer business logic.

Do not refactor unrelated Lambdas.

---

# Verification

Before completing the task, verify:

1. `postDisposalRequest` imports common helpers from `shared_utils`.

2. No shared helper implementation has been duplicated inside the Lambda source.

3. The shared utilities are included in the generated Lambda ZIP.

4. The Lambda supports multiple assets.

5. Identified assets are retrieved from `assets_table`.

6. Authoritative identified-asset information comes from the database.

7. Unidentified assets are supported without an `assets_table` lookup.

8. Unidentified assets are not assigned fake asset IDs.

9. Duplicate non-empty `assetID` values are rejected.

10. All assets are validated before the DynamoDB disposal record is created.

11. A backend UUID is generated for `disposalId`.

12. `disposalCreated` is generated by the backend as an ISO timestamp.

13. Initial status is:

```text
pending
```

14. One DynamoDB item contains all assets under:

```text
assets[]
```

15. Each asset initially stores:

```text
images: []
```

16. Presigned URLs retain:

```text
assetIndex
```

17. Identified asset presigned responses also retain:

```text
assetID
```

18. Presigned URL `ContentType` matches frontend upload metadata.

19. Creating the request does not modify `assets_table`.

20. No Terraform infrastructure resources are created or replaced.

21. Existing Lambda/environment/resource configuration is only inspected/reused.

22. Python syntax checks pass.

23. Existing tests remain passing where available.

---

# Codex Completion Summary

After implementation, provide:

```text
Files created
Files modified

postDisposalRequest implementation summary

Frontend payload assumptions

Identified asset validation performed

Unidentified asset handling

Shared helper functions reused

How shared_utils is injected into the ZIP

DynamoDB fields written

Presigned URL structure

Scheduler behaviour

Validation/error handling added

Tests/checks performed

Anything intentionally deferred
```

Do not proceed to another disposal Lambda after completing this task.
