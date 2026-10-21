Update the existing Lambda responsible for creating asset disposal requests.

## Objective

Add duplicate-disposal protection before a new disposal request is written to DynamoDB.

The Lambda currently creates disposal requests in:

`crud-nosql-app-assets-disposal-table`

and retrieves registered assets from:

`crud-nosql-app-assets-table`.

## Duplicate matching rule

For every submitted asset, determine whether either of these identifiers is available:

- `assetID`
- serial number

The asset must be considered already present in a disposal request when **either identifier matches** an asset in an existing applicable disposal request.

The rule is:

```text
existing.assetID == submitted.assetID
OR
existing.serialNumber == submitted.serialNumber
```

Therefore:

- same `assetID` → reject;
- same serial number → reject;
- both match → reject;
- `assetID` matches but serial number differs → still reject;
- serial number matches but `assetID` differs → still reject;
- only `assetID` exists and it matches → reject;
- only serial number exists and it matches → reject;
- neither `assetID` nor serial number exists → do not perform duplicate matching and allow the asset to continue through the normal POST flow.

If neither identifier exists, assume the administrator can manually distinguish the unidentified asset.

Do not require both identifiers to exist.

## Identifier handling

For registered assets, retrieve the authoritative asset record from:

`crud-nosql-app-assets-table`

using the existing `AssetIDIndex` logic.

Use the authoritative asset data to determine the serial number where available.

Inspect the repository first to determine the actual serial-number field name already used by the project, for example:

```text
serialNo
serialNumber
serial_number
serial
```

Do not introduce a new field name if one already exists.

If the registered asset contains a serial number and the normalized disposal asset currently does not persist it, add the existing serial-number field to the processed asset where appropriate.

For unidentified assets, use the frontend-provided serial number if one exists.

## Duplicate lookup

Before creating the disposal request, check the existing records in:

`crud-nosql-app-assets-disposal-table`

for assets where either:

```text
asset.assetID == submitted_asset_id
```

or:

```text
asset.serialNumber == submitted_serial_number
```

Only compare an identifier when the submitted identifier is non-empty.

For example:

```python
asset_id_match = (
    submitted_asset_id
    and existing_asset_id
    and submitted_asset_id == existing_asset_id
)

serial_match = (
    submitted_serial
    and existing_serial
    and submitted_serial == existing_serial
)

duplicate = asset_id_match or serial_match
```

Normalize strings appropriately before comparing so whitespace or inconsistent casing does not cause obvious duplicate assets to bypass validation.

Do not accidentally compare empty strings.

## Response when duplicate exists

If an applicable disposal request already contains the asset, reject the entire new disposal request with:

```http
409 Conflict
```

Return useful information such as:

```json
{
  "message": "A disposal request already exists for this asset",
  "assetID": "ASSET-001",
  "serialNumber": "ABC123",
  "existingDisposalId": "..."
}
```

Only return identifier fields that actually exist.

Do not expose internal DynamoDB information.

## Important: inspect the existing data model first

Before implementing the change, inspect the repository to determine:

- the actual serial-number field name;
- how `assetID` is stored;
- how serial numbers are stored in the assets table;
- how serial numbers are stored in disposal `assets[]`;
- the key structure of `crud-nosql-app-assets-disposal-table`;
- existing GSIs;
- existing Terraform/IaC;
- disposal lifecycle statuses;
- existing DynamoDB helper functions.

Do not guess schema details.

## Existing disposal statuses

Inspect the current disposal lifecycle and determine which statuses should prevent another disposal request.

Likely statuses may include:

```text
pending
approved
disposed
cancelled
rejected
expired
```

Preserve existing business behaviour.

For example, if `cancelled`, `rejected`, or `expired` requests are considered closed and assets may subsequently be submitted again, exclude them from duplicate blocking.

Do not arbitrarily define this without checking the existing workflow.

Document the final status logic in the implementation summary.

## Current-request duplicate validation

Preserve the existing duplicate validation inside the same incoming request.

Currently duplicate `assetID` values are checked.

Extend this validation if appropriate so the same incoming request also cannot contain two assets with the same non-empty serial number.

The same OR principle applies:

- duplicate `assetID` inside the incoming request → reject;
- duplicate serial number inside the incoming request → reject;
- neither identifier exists → allow.

Do not treat two unidentified assets with neither field as duplicates.

## DynamoDB design

Avoid an inefficient full-table `Scan` unless the current DynamoDB design leaves no practical alternative.

Because disposal assets are currently stored inside an `assets[]` list, inspect whether the current design can efficiently support the lookup.

If a scan is currently unavoidable, document that clearly.

Do not introduce a major data-model redesign unless necessary.

If a lightweight index or auxiliary lookup record is clearly the correct solution, implement the smallest appropriate change.

## Race conditions

Consider concurrent requests.

Two POST requests for the same asset could potentially both perform a duplicate check before either request has been saved.

Determine whether the current DynamoDB model can provide atomic uniqueness protection for:

```text
assetID
OR
serial number
```

If it cannot because identifiers are stored inside nested `assets[]` records, document this limitation.

Do not claim the solution is race-condition safe unless it actually is.

## IAM / permissions

Inspect the Lambda's IAM configuration and Terraform/IaC.

Verify that the Lambda has all permissions required by the final implementation.

Depending on the implementation this may include:

```text
dynamodb:GetItem
dynamodb:Query
dynamodb:Scan
dynamodb:PutItem
dynamodb:TransactWriteItems
```

Only add permissions actually required.

Use least privilege.

If an index is queried, confirm the IAM resource covers the index ARN where required.

Also make sure the existing permissions required for:

- `crud-nosql-app-assets-table`;
- `crud-nosql-app-assets-disposal-table`;
- S3 presigned uploads;

remain intact.

Make IAM changes in Terraform/IaC rather than manually changing only the deployed role.

## Existing functionality that must remain unchanged

Do not break:

- `_get_registered_asset`;
- `AssetIDIndex`;
- `_validate_asset_eligibility`;
- unidentified assets;
- Cognito requestor identity;
- presigned image uploads;
- CORS;
- shared utilities;
- disposal ID creation;
- request timestamps;
- request status;
- current response structure except where required;
- DynamoDB conditional creation.

## Error handling

Expected behaviour:

```text
400 - invalid request
401 - unauthorized
404 - registered asset not found
409 - asset already exists in an applicable disposal request
500 - unexpected backend failure
```

Use a specific duplicate-disposal error path rather than allowing duplicate detection to become a generic `500`.

## Tests / validation

Verify at minimum:

1. Existing disposal has same `assetID` → `409`.
2. Existing disposal has same serial number → `409`.
3. Existing disposal has both matching → `409`.
4. Same `assetID`, different serial number → `409`.
5. Different `assetID`, same serial number → `409`.
6. Only `assetID` provided and it matches → `409`.
7. Only serial number provided and it matches → `409`.
8. `assetID` exists but no match → request continues.
9. Serial number exists but no match → request continues.
10. Neither `assetID` nor serial number exists → request continues.
11. Two unidentified assets without either identifier in the same request → allowed.
12. Duplicate `assetID` within the same incoming request → `400`.
13. Duplicate serial number within the same incoming request → `400`.
14. One asset among several matches an existing disposal → entire POST is rejected before `put_item`.
15. Closed disposal statuses behave according to existing lifecycle rules.
16. Presigned uploads still work.
17. IAM permissions are sufficient.

## Final output

After completing the change, provide:

1. Files changed.
2. Exact duplicate-matching rule implemented.
3. Actual serial-number field name found.
4. Which disposal statuses block another request.
5. DynamoDB lookup method used.
6. Whether a Scan, Query, index, or auxiliary record was required.
7. IAM permissions reviewed.
8. IAM permissions added or modified.
9. Race-condition considerations.
10. Tests or validation performed.

Do not make unrelated changes.
