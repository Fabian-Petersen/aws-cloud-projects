Implement a new `deleteTransferById` backend function by using the existing `deleteDisposalById` implementation as the primary reference.

## Objective

Create transfer deletion functionality that behaves consistently with `deleteDisposalById`, but operates on the asset transfer data and related transfer resources.

Do not redesign the deletion pattern.

## First inspect the codebase

Before changing anything, inspect:

- `deleteDisposalById`
- the transfer table configuration
- existing transfer GET functions
- transfer-related DynamoDB key structure
- existing shared response/CORS utilities
- transfer-related S3 object paths, if applicable
- API Gateway/Terraform routes for delete functions
- IAM permissions used by similar delete Lambdas
- frontend/backend references to transfer deletion, if any

Use `deleteDisposalById` as the main implementation pattern and keep behaviour consistent with it.

## Function

Create or implement:

```text
deleteTransferById
```

The function must delete a transfer request by its transfer ID.

The current transfer table uses:

```text
transferId
```

as the partition key.

Inspect the actual Terraform/table definition and existing transfer functions to confirm this before implementation.

Do not assume an additional sort key unless the current table actually uses one.

## Required behaviour

Follow the same overall sequence and response structure used by `deleteDisposalById`.

The function should:

1. Read the transfer ID from:

```python
event.get("pathParameters", {}).get("id")
```

2. Return `400` if the ID is missing.

3. Retrieve the existing transfer record before deleting it.

4. Return `404` if the transfer does not exist.

5. Delete the DynamoDB transfer record using the correct key.

6. If `deleteDisposalById` also removes related S3 objects, apply the equivalent behaviour to transfer-related files only where applicable.

7. Return the same style of success response used by `deleteDisposalById`.

8. Use the same error handling and logging conventions.

## S3 cleanup

Inspect the transfer object structure and existing upload paths.

Transfer-related files may exist under paths such as:

```text
transfers/<transferId>/
```

including:

```text
transfers/<transferId>/invoices/
transfers/<transferId>/assets/<assetID>/images/
```

Do not blindly delete S3 objects unless `deleteDisposalById` already performs equivalent cleanup and this matches the current transfer storage structure.

If transfer deletion is intended to remove associated files, delete only objects belonging to that `transferId`.

Do not affect files belonging to other transfers.

Reuse the same S3 helper/pagination pattern used by existing delete functions.

## Status/business rules

Inspect whether `deleteDisposalById` restricts deletion based on status.

Apply the equivalent transfer rule only if the current project has one.

Do not invent new workflow rules.

For example, do not automatically block deletion of `approved`, `in-transit`, or `received` transfers unless existing backend logic or business rules already require this.

If deletion is only allowed for certain statuses, reuse the existing project convention and return the appropriate response.

## Related records

Check whether a transfer has related records such as:

- notifications
- scheduler entries
- approval timeout schedules
- transfer events
- other DynamoDB records

Do not automatically delete these unless the existing `deleteDisposalById` pattern or current transfer architecture clearly requires cleanup.

If related cleanup already exists elsewhere in the transfer workflow, reuse that logic rather than creating a separate approach.

## Shared utilities

Reuse
