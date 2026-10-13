Status = `Pending`

## Task: Update the existing OpenAPI YAML documentation to match the current application

Review the entire project and update the existing OpenAPI/Swagger YAML file "Testing\03_Testing_CRUD_NoSQL\API_Docs\openapi_20261012.yaml" so that it accurately documents the API **as it exists in the current codebase**.

This is a **documentation-only task**.

### CRITICAL SCOPE RESTRICTION

You may modify **ONLY the existing OpenAPI YAML file**.

Do **NOT** modify:

- frontend source code
- backend Lambda functions
- Terraform
- API Gateway configuration
- schemas
- utilities
- tests
- package files
- configuration files
- README files
- deployment files
- any other YAML files
- any other file in the repository

Do not refactor, fix, rename, reformat, or improve application code.

The application implementation is the source of truth.

Your job is to make the OpenAPI YAML reflect the current implementation — **not to change the implementation to match the YAML**.

---

# 1. Discover the actual API routes

Inspect the repository and determine every API endpoint currently used by the application.

Use all relevant sources, including:

- frontend API hooks/utilities
- axios/fetch requests
- React Query hooks
- frontend resource paths
- backend Lambda handlers
- API Gateway/Terraform route definitions
- Lambda event path handling
- path parameters
- query-string parameters

Search for route patterns such as:

```text
/api/
jobs
assets
users
comments
dashboard
transfers
disposals
notifications
locations
verification
jobcard
approve
reject
cancel
complete
action
```

Do not assume the existing YAML routes are correct.

Compare the documented routes against the actual routes implemented in the repository.

The public API may be exposed through:

```text
https://crud-nosql.app.fabian-portfolio.net
```

If the frontend calls routes beginning with `/api/...`, document the actual public route used by the frontend/API Gateway rather than preserving outdated paths merely because they already exist in the YAML.

---

# 2. Determine HTTP methods

For every route determine its real HTTP method:

```text
GET
POST
PUT
PATCH
DELETE
```

Only document methods actually implemented.

Do not invent methods based on REST conventions.

For example, inspect whether the frontend/backend actually performs:

```text
POST /api/jobs/{id}/approve
POST /api/jobs/{id}/reject
GET /api/jobs/{id}/jobcard
```

rather than relying on what the old YAML says.

---

# 3. Determine path parameters

Document the exact path parameters used by the implementation.

Examples could include:

```text
{id}
{jobId}
{userId}
{transferId}
{disposalId}
{request_id}
```

Determine their actual type from the implementation.

Do not declare an ID as:

```yaml
type: integer
format: int64
```

if the application actually uses UUID/string identifiers.

Use the parameter name actually expected by API Gateway/Lambda.

---

# 4. Determine query parameters

Inspect the frontend and Lambda handlers for query parameters.

Examples may include:

```text
status
group
location
year
month
sub
action_id
```

For each query parameter document:

- name
- location: `query`
- required/optional
- data type
- enum values where the implementation constrains them
- description where useful

Do not retain outdated query parameters that are no longer used.

---

# 5. Determine request payloads

For every POST/PUT/PATCH endpoint inspect the actual frontend payload and Lambda handler.

Document the JSON structure actually sent.

Use:

```yaml
requestBody:
  required: true
  content:
    application/json:
```

where appropriate.

Capture:

- field names
- nested objects
- arrays
- required fields
- optional fields
- data types
- enums
- date/date-time fields

Examples of payloads that must be verified from the code include:

### Maintenance requests

Inspect the actual create-maintenance-request payload including fields such as:

```text
location
type
priority
impact
jobComments
description
breakdown_time
assets
```

and the structure of each item in:

```text
assets[]
```

### Job approval

Inspect the exact payload currently sent when approving a job.

Possible fields include:

```text
assign_to_group
assign_to_sub
assign_to_name
targetDate
status
selectedRowId
```

Do not assume all of these are still present. Verify them.

### Job rejection

Inspect the actual rejection payload.

Possible fields include:

```text
reject_message
status
selectedRowId
```

Document the actual structure instead of using legacy schemas such as `Pet`.

### Job completion/action

Inspect the current maintenance-action/completion payload.

This may contain data such as:

```text
start_time
end_time
total_km
work_completed
status
root_cause
findings
contractor
total_cost_contractor
invoices
images
signature
signedBy
parts
total_cost_parts
sundries
```

Document the actual implementation, including nested arrays/objects.

Do not infer fields solely from this prompt. The repository is the source of truth.

### Assets

Inspect create/update asset payloads including:

```text
location
business_unit
area
equipment
assetType
category
replacementValue
assetID
condition
serialNumber
additional_notes
images
deleted_image_keys
```

Verify which fields belong to create versus update.

### Asset transfers

Inspect all implemented transfer lifecycle payloads, including where applicable:

```text
create
approve
reject
in-transit
receive
cancel
```

Document nested:

```text
assets[]
images[]
invoices[]
```

from the implementation.

### Disposals

Inspect the current disposal endpoints and their payloads, including:

```text
create
requests
approve
reject
cancel
```

Use the exact payload fields used by the application.

### Users

Inspect:

```text
create user
update user
get current user
resend temporary password
```

and document the actual request structures.

### Comments

Inspect how comments are created/read/updated and document their actual body structure.

---

# 6. Determine actual response structures

For every endpoint inspect what the Lambda actually returns.

Do not simply document the DynamoDB item schema if the Lambda wraps or transforms it.

Check whether responses look like:

```json
{
  "message": "...",
  "data": {}
}
```

or:

```json
[]
```

or:

```json
{
  "presigned_urls": []
}
```

or another structure.

Capture the real shape.

For each response document appropriate fields and schemas.

---

# 7. Presigned URL workflows

Several application operations use S3 presigned URLs.

Where applicable document:

- upload metadata sent to the API
- returned presigned URL structure
- S3 object metadata returned
- `filename`
- `content_type`
- `key`
- `url`
- upload URL
- deleted image keys

Do not document the binary image itself as the API request body if the actual API receives JSON metadata and returns a presigned S3 URL.

---

# 8. Jobcard endpoint

Pay particular attention to the current jobcard route.

Inspect both frontend and backend.

The current application uses a route in the form:

```text
/api/jobs/{id}/jobcard
```

where `{id}` is associated with the maintenance action.

Determine exactly:

- path
- HTTP method
- meaning of `{id}`
- returned JSON
- presigned PDF URL structure
- relevant error responses

Remove any remaining Petstore schemas from this endpoint.

---

# 9. Authentication

Inspect the actual API Gateway/Terraform authentication configuration.

The application uses Cognito/JWT authentication for protected routes.

Document the actual authentication scheme consistently.

Prefer an OpenAPI bearer security scheme such as:

```yaml
BearerAuth:
  type: http
  scheme: bearer
  bearerFormat: JWT
```

where this matches the implementation.

Do not retain fake Petstore OAuth scopes such as:

```yaml
petstore_auth:
  - write:pets
  - read:pets
```

unless such a scheme genuinely exists in this repository.

Similarly, do not retain `api_key` authentication on routes if the implementation actually uses Cognito JWT bearer authentication.

Public routes, if any, should be documented based on the implementation.

---

# 10. Components / schemas

Update:

```yaml
components:
  schemas:
```

to match the real domain models.

Reuse schemas where sensible.

Potential schema groups include:

```text
User
Asset
MaintenanceRequest
MaintenanceAction
JobApproval
JobRejection
Comment
AssetTransfer
Disposal
Notification
DashboardMetric
PresignedUpload
JobcardResponse
ErrorResponse
```

Only introduce schemas supported by the implementation.

Remove or replace obsolete generic schemas such as:

```text
Pet
Order
ApiResponse
```

where they are remnants of the Swagger Petstore template and do not represent actual application responses.

---

# 11. Data types

Correct inaccurate data types.

Examples:

UUIDs should generally be:

```yaml
type: string
format: uuid
```

if they are real UUIDs.

ISO timestamps should generally be:

```yaml
type: string
format: date-time
```

Date-only values should generally be:

```yaml
type: string
format: date
```

Currency/cost fields should use an appropriate numeric type.

Boolean values must not be documented as strings if the API returns actual booleans.

Arrays must describe their item type.

Nested objects must have their properties documented.

---

# 12. Status enums

Inspect backend and frontend code for actual allowed statuses.

Do not blindly preserve existing enum values.

Examples that may exist in different modules include:

```text
pending
approved
in-progress
in_progress
completed
complete
rejected
cancelled
cancel
expired
received
in-transit
```

Use the **exact strings actually used by each API**.

Do not normalize or rename application values merely for documentation consistency.

---

# 13. Response status codes

Determine the status codes actually returned by the handlers where possible.

Document applicable responses such as:

```text
200
201
400
401
403
404
409
500
```

Do not invent unsupported status codes.

Use a shared error schema where practical if the Lambda responses use a common error structure.

---

# 14. Remove Swagger Petstore remnants

The current YAML originated partly from the Swagger Petstore example.

Remove obsolete references such as:

```text
Pet
Order
petstore_auth
write:pets
read:pets
sample pet descriptions
Pet Store repository links
Petstore API descriptions
```

provided they are not part of the actual application.

Update the API metadata so that it describes the Atlantic Meat Maintenance and Asset Management application.

Do not unnecessarily rewrite metadata that is already correct.

---

# 15. Preserve custom implementation metadata where accurate

The YAML currently contains useful custom properties such as:

```yaml
x-lambda-runtime:
x-lambda-function:
x-database:
x-database-1:
x-database-2:
```

Preserve these where they are still correct.

Update their values only when repository inspection proves that they are outdated.

For newly documented routes, add the same metadata pattern where the relevant Lambda/database can be confidently determined.

Do not guess.

---

# 16. Examples

Where the actual code provides enough information, add realistic examples for request and response bodies.

Examples should use safe dummy values such
