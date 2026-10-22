# Investigate unexpected Terraform DynamoDB resource replacement

## Context

I changed the Terraform module source for DynamoDB from a **local module** to the same module hosted in a **different repository / remote source**.

See changes made in the remote repository

```terraform
locals {
  module_name    = "dynamoDB"
  module_version = "v1.0.2"
}

  tags = merge(var.tags, {
    # Project = var.project_name
    # Env     = var.env
    Module        = local.module_name
    ModuleVersion = local.module_version
    Name          = each.key
  })
```

The actual DynamoDB configuration should be functionally identical.

The only intended change made to the remote module was the addition of **tags**.

After running `terraform plan`, Terraform now wants to **destroy and recreate 2 DynamoDB-related resources**.

I do **not** expect these resources to be replaced simply because:

- the module source changed from local to remote; and
- tags were added.

## Task

Investigate why Terraform is proposing destruction and recreation of these two resources.

### Important constraints

- **Do not modify any Terraform files.**
- **Do not run `terraform apply`.**
- **Do not run `terraform destroy`.**
- **Do not run any command that modifies Terraform state.**
- Do not use `terraform state mv`, `terraform import`, `terraform state rm`, `terraform apply -refresh-only`, or similar state-changing commands.
- You may inspect code, configuration, lock files, state references, and existing plan output.
- If Terraform commands are required, only use read-only/safe commands such as `terraform validate`, `terraform providers`, `terraform state list`, `terraform state show`, and `terraform plan`.
- Do not make unrelated changes.

## Investigation

Compare the previous local module and the new remote module and identify exactly what Terraform considers different.

Check the following areas.

### 1. Terraform resource addresses

Determine whether changing the module source caused any change to the Terraform resource addresses.

Compare examples such as:

```text
module.dynamodb.aws_dynamodb_table.example
```

between the current state and the current configuration.

Check whether:

- the module block name changed;
- nested module names changed;
- `for_each` keys changed;
- `count` indexes changed;
- resource names inside the module changed.

Changing only the module `source` should normally not change the state address, so explicitly verify this.

### 2. Exact replacement reason from the plan

Inspect the Terraform plan and identify the attributes marked with:

```text
# forces replacement
```

or any equivalent replacement indicator.

For each of the two resources being replaced, report:

- Terraform resource address;
- resource type;
- attribute causing replacement;
- old value;
- new value;
- whether the difference originates from the module, provider, variable input, or state.

Do not simply state that Terraform detects drift. Identify the exact field responsible.

### 3. Compare local vs remote module

Perform a focused comparison of the local module version previously used and the current remote module.

Check especially:

- resource names;
- `for_each`;
- `count`;
- keys used by `for_each`;
- DynamoDB table name;
- billing mode;
- hash key;
- range key;
- attributes;
- GSIs;
- LSIs;
- stream settings;
- encryption/KMS configuration;
- deletion protection;
- TTL;
- replicas/global tables;
- lifecycle blocks;
- `ignore_changes`;
- provider aliases;
- default values;
- variable types;
- conditional expressions;
- dynamic blocks;
- tags and `tags_all`.

Ignore formatting-only differences.

### 4. Tags

Verify whether the newly added tags themselves are responsible.

Determine whether the change is only:

```hcl
tags = ...
```

or whether introducing tags indirectly changes:

- `for_each`;
- locals;
- object structures;
- module inputs;
- resource naming;
- conditional creation;
- provider `default_tags`;
- `tags_all`.

Tags should generally be an in-place update for a DynamoDB table, so flag anything unusual if tags are causing replacement.

### 5. Provider version/schema differences
