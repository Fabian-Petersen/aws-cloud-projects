Inspect the repository for existing Lambda functions that delete records and associated S3 files, especially maintenance/job request delete functions and any other delete handlers using the project's shared utilities and infrastructure patterns.

Then create the equivalent delete functionality for disposal requests.

## Objective

Create a delete Lambda for disposal requests that follows the same architecture, coding style, shared helpers, response handling, CORS handling, IAM pattern, and Terraform/IaC conventions already used by the existing delete functions.

Do not invent a new pattern if the repository already has an established one.

Note: `The Disposal lambdas as created with the generic helpers in the layers/python/shared_utils to prevent creating the same functions again.`

## Disposal table

Use:

```text
crud-nosql-app-assets-disposal-table
```

The disposal record is identified by:

```text
disposalId
```

Inspect the table definition first to confirm the full key structure, including whether `disposalCreated` is also required as a sort key.

Do not assume the schema without checking the Terraform/IaC or existing disposal Lambdas.

## Required behaviour

The new delete Lambda must:

1. Read the disposal ID from the existing API path parameter convention.
2. Find the disposal request in DynamoDB.
3. Return `404` if the request does not exist.
4. Delete all S3 objects associated with that disposal request.
5. Delete the disposal request from DynamoDB.
6. Return the same style of success response used by the existing delete functions.

## S3 cleanup

Inspect how disposal files are currently stored.

The disposal POST flow currently creates image keys beneath a disposal-specific path such as:

```text
disposals/{disposalId}/...
```

Do not assume that every uploaded object is persisted inside the DynamoDB `assets[].images` structure.

Inspect the existing disposal code and determine the safest existing-project-compatible way to remove all files belonging to the disposal.

Prefer the repository's established deletion pattern.

If the disposal uses a predictable S3 prefix such as:

```text
disposals/{disposalId}/
```

then delete all objects beneath that prefix if this is consistent with the application's current S3 design.

Ensure pagination is handled correctly if more than 1,000 objects could theoretically exist.

Do not delete objects outside the disposal's own prefix.

## Existing delete functions

Before implementing, inspect existing delete Lambdas for patterns such as:

- request/job deletion;
- asset deletion;
- transfer deletion;
- disposal-related cleanup if any;
- shared response helpers;
- CORS helpers;
- request metadata helpers;
- DynamoDB helpers;
- S3 helpers.

Reuse those patterns wherever appropriate.

If shared helpers already exist for deleting an S3 prefix or DynamoDB records, use them instead of duplicating logic.

## Shared utilities

The current project uses shared utilities such as:

```text
shared_utils._response
shared_utils.cors
shared_utils.dynamodb
shared_utils.request
shared_utils.s3
```

Inspect the existing delete Lambdas and use the same shared utilities and conventions.

Do not copy the
