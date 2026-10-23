status = `Pending`

# Implement manual asset verification backend

I added a new API route:

`api/assets/:id/verify-manual`

I also created a new Lambda by copying the existing asset verification Lambda:

`postAssetVerifyManual.py`

The copied Lambda currently contains the same logic as the normal asset verification flow.

## Objective

Update `Testing\03_Testing_CRUD_NoSQL\lambdas\assets\postAssetVerifyManual` so that it handles a manual asset verification request from the frontend.

The new implementation must follow the existing verification architecture, data structures, authentication patterns, DynamoDB conventions, S3 structure, presigned upload workflow, response helpers, and IAM assumptions already used elsewhere in the project.

Do not redesign the verification system.

## Required workflow

When the frontend calls:

`POST api/assets/:id/verify-manual`

the Lambda must:

1. Extract the authenticated user from the existing Cognito/JWT claims using the same shared utilities/patterns used by the other Lambdas.
2. Read the asset ID from the route parameter.
3. Validate that the asset exists using the same asset lookup logic used by the normal verification Lambda.(The UUID must be used as the barcode ID does not exist or is not known).
4. Validate the user and any existing permissions/location restrictions using the same rules already used by the normal asset verification flow.
5. Accept the manual verification details sent by the frontend.
6. Create/update the appropriate record in the existing verification DynamoDB table.
7. Clearly identify the verification as a manual verification.
8. Store the reason supplied by the user explaining why the asset was manually verified.
9. Support images attached specifically to this verification instance.
10. Generate S3 presigned upload URLs for those images.
11. Return the presigned URLs and required image metadata to the frontend.
12. Ensure the verification record can subsequently be updated with the uploaded image metadata/keys using the same pattern already used by other image upload workflows.

## Manual verification fields

Inspect the frontend request and existing verification schema before deciding exact field names. See the `Testing\03_Testing_CRUD_NoSQL\lambdas\assets\postAssetVerifyManual\event.json` with the frontend request example.

Reuse existing field conventions wherever possible.

The verification record should contain enough information to identify that this was manually verified, for example using the project's existing naming conventions for fields equivalent to:

- verification type/method = manual
- manual verification reason
- verified by user name
- verified by Cognito `sub`
- verification timestamp
- asset ID
- location/site where applicable
- verification status
- verification image metadata

Do not introduce duplicate fields if equivalent fields already exist in the verification records.

## Manual verification reason

The manual verification reason must:

- be provided by the frontend;
- be validated as non-empty;
- be stored against this specific verification instance;
- remain available for audit/history purposes.

Return a `400` response if the manual verification reason is required but missing.

## Images and S3

Manual verification images must be stored under the existing verification area in the application's S3 bucket.

Before implementing the path, inspect the existing verification Lambdas and other Lambdas that generate presigned image uploads.

Follow the same directory structure and naming strategy already used by the project.

Use the existing structure under something equivalent to:

`verification/...`

Do not create a completely new S3 hierarchy unless required.

The path must make the images traceable to the specific verification instance and asset.

For example, if consistent with the existing implementation:

`verification/<asset-id>/<verification-id>/images/<filename>`

However, use the project's existing structure if it differs.

## Presigned URL behaviour

Follow the existing project pattern for presigned uploads.

For every image requested by the frontend:

- create the final S3 object key;
- preserve/validate the expected content type;
- generate a presigned `PUT` URL;
- return the key and upload URL to the frontend;
- return any other metadata required by the existing frontend upload utilities.

Do not upload image binary data through API Gateway/Lambda.

The frontend should upload directly to S3 using the presigned URLs.

Make sure the Content-Type expected by the presigned request matches what the frontend must send.

## Verification image metadata

Inspect how the existing application stores image references for:

- normal asset verification;
- maintenance requests;
- assets;
- transfers/disposals if relevant.

Use the same metadata format rather than creating another image representation.

The DynamoDB verification record should ultimately reference S3 object keys/metadata rather than storing large image payloads.

## Existing verification logic

Compare `postAssetVerifyManual.py` against the original asset verification Lambda.

Reuse applicable logic for:

- asset lookup;
- user lookup;
- authorization;
- location validation;
- verification timestamps;
- verification table writes;
- existing verification IDs;
- DynamoDB serialization;
- response formatting;
- CORS;
- exception handling.

Only change behaviour required for manual verification.

Do not modify the normal verification Lambda unless a shared helper absolutely requires a backwards-compatible change.

## Existing verification history

Manual verification must become part of the same verification history/audit trail as normal verification.

Do not overwrite historical verification records unless the existing verification design intentionally uses update semantics.

Inspect the verification table keys and existing Lambda behaviour before making this decision.

## Error responses

Use the project's existing response helper and error format.

At minimum handle:

- `400` – invalid request / missing manual verification reason / malformed image metadata
- `401` – authentication failure where applicable
- `403` – user not permitted to verify the asset
- `404` – asset not found
- `500` – unexpected backend failure

Do not expose internal AWS errors or stack traces to the frontend.

Log enough context for CloudWatch debugging.

## IAM and infrastructure

Before finalising the Lambda, inspect the Terraform/resources for the copied/manual Lambda.

Confirm that the Lambda execution role already has the permissions required for:

- reading the asset table;
- reading user/location information if required;
- reading/writing the verification table;
- generating/using the required S3 verification object paths;
- any GSIs queried by the Lambda.

Do NOT broaden IAM permissions unnecessarily.

Do NOT use `s3:*`, `dynamodb:*`, or wildcard resource permissions unless they are already intentionally used by the existing infrastructure.

If permissions are missing, report the exact IAM change required instead of broadly changing unrelated policies.

## Route integration

Verify that:

`api/assets/:id/verify-manual`

is connected to the intended Lambda and uses the same Cognito authorizer/security configuration as the other protected asset verification routes.

Do not modify unrelated API Gateway routes.

## Important guardrails

- First inspect the existing normal asset verification Lambda.
- Inspect the verification DynamoDB table schema before changing write logic.
- Inspect existing S3 verification image handling.
- Inspect frontend API calls/types for the new manual verification flow if they already exist.
- Reuse existing shared utilities.
- Preserve existing naming conventions.
- Do not redesign the backend.
- Do not rename unrelated resources.
- Do not refactor unrelated code.
- Do not change existing API contracts unless required for this route.
- Do not change the normal verification behaviour.
- Do not run Terraform apply.
- Do not deploy anything.
- Do not run a full application build.
- Do not run broad repository-wide tests.
- Limit validation to the changed Lambda and directly related code.
- Do not generate additional documentation unless required to explain a necessary infrastructure change.

## Expected Codex output

After implementation, provide a concise summary containing:

1. Files changed.
2. Manual verification request payload expected from the frontend.
3. DynamoDB fields written/updated.
4. S3 key structure used for verification images.
5. Shape of the presigned URL response.
6. Authentication/authorization checks performed.
7. Any IAM or Terraform changes required.
8. Any assumptions made based on the existing normal verification flow.

Do not make unrelated changes.