Review the new disposal update Lambda and make only the changes necessary to ensure it is fully compliant with the existing AWS resources, API configuration, DynamoDB schema, S3 structure, and IAM permissions already defined in this repository.

Do not redesign the function or infrastructure.

## Objective

Validate that the disposal update Lambda correctly integrates with the resources that already exist.

The Lambda must be checked against the actual repository configuration for:

- DynamoDB table name and key structure
- S3 bucket and object paths
- API Gateway route and HTTP method
- Cognito authorizer
- Lambda naming conventions
- environment variables
- Terraform resources
- IAM policies
- Lambda invoke permissions
- CORS conventions
- shared utilities

Do not rely on assumptions made in the Lambda code.

## First inspect the existing resources

Before modifying anything, inspect the Terraform/infrastructure and relevant backend code.

Identify the actual:

- disposal DynamoDB table
- partition key
- sort key, if any
- disposal image S3 bucket
- disposal image key/prefix convention
- existing disposal API resource hierarchy
- HTTP method expected by `DisposalUpdateForm`
- Cognito authorizer configuration
- Lambda execution role pattern
- existing IAM policy structure
- existing Lambda environment variables
- shared response/CORS utilities
- equivalent update Lambdas already deployed by the project

Treat the repository configuration as the source of truth.

## DynamoDB compliance

Confirm the disposal table's actual key schema.

The Lambda currently expects to retrieve a disposal by `disposalId` and may resolve `disposalCreated` as a sort key.

Verify this against the actual table.

If the table uses:

```text
PK: disposalId
SK: disposalCreated
```

ensure the Lambda queries and updates using the correct full key.

If the table uses only:

```text
PK: disposalId
```

remove unnecessary query/sort-key logic and use the established `get_item`/`update_item` pattern.

Do not change the DynamoDB table schema.

Check whether the Lambda requires any indexes. It should not use a GSI unless the existing schema requires it.

## Table name

Do not hardcode a guessed table name if the rest of the project uses environment variables.

Inspect existing disposal Lambdas and follow the same convention.

For example, if existing Lambdas use:

```python
TABLE_NAME = os.environ["TABLE_NAME"]
```

follow that pattern.

Do not introduce a different environment variable naming convention.

## S3 compliance

Inspect the actual disposal upload/create functions and determine where disposal images are stored.

Verify the exact key pattern.

Do not assume:

```text
disposals/{disposalId}/...
```

unless that is
