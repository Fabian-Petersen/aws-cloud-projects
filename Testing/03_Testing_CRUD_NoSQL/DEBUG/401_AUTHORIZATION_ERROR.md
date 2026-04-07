# 401 Unauthorized - Troubleshooting Summary

## Problem

API requests returning `401 Unauthorized` after Cognito User Pool was recreated with a new ID.

## Root Cause Investigation

### 1. Stale JWT Tokens

- **Checked:** Cleared `localStorage`, signed out and back in
- **Result:** Problem persisted — tokens were not the issue

### 2. Amplify Configuration

- **Checked:** `Amplify.getConfig()` returned empty
- **Finding:** `console.log` was placed _before_ `Amplify.configure()` — logging order issue, not a real problem
- **Verified:** Amplify config had the correct `userPoolId` and `userPoolClientId`

### 3. API Client (axios)

- **Checked:** `apiClient.ts` interceptor was correctly attaching the Bearer token
- **Checked:** `getIdToken()` using `fetchAuthSession()` was correctly returning the `idToken`
- **Result:** Token retrieval and attachment were fine

### 4. API Gateway Authorizer

- **Checked:** `aws_api_gateway_authorizer.cognito` was using `var.cognito_arn`
- **Verified:** ARN was dynamically sourced via `module.cognito.cognito_userpool_arn` and had the correct new User Pool ID
- **Finding:** API Gateway was not redeployed after the User Pool was recreated

### 5. Checked Bearer Token

- **Checked:** copy token from network tab and insert into jwt.io.
- **Verified:** Token had the correct userpool_id, see sample output: <br>

```json
{
  "sub": "e19c3208-c041-70be-d6e8-a88453870f6c",
  "cognito:groups": ["admin"],
  "email_verified": true,
  "iss": "https://cognito-idp.af-south-1.amazonaws.com/af-south-1_A4wjuHPlq",
  "cognito:username": "e19c3208-c041-70be-d6e8-a88453870f6c",
  "origin_jti": "b2e1bab9-c534-41b9-9417-6542520f84eb",
  "aud": "3hpqstl3diqlrrfau7t9luirj3",
  "event_id": "5b4cb03a-306f-4ee1-9cd8-6bb33cb26fdf",
  "token_use": "id",
  "auth_time": 1775120250,
  "name": "fabian",
  "exp": 1775123850,
  "iat": 1775120250,
  "family_name": "petersen",
  "jti": "8aacda30-488a-40a0-aa5d-5ed293a8b1f9",
  "email": "fpetersen2@gmail.com"
}
```

- **Finding:** Token had the correct credentials

## Fix

### Force API Gateway Redeployment

Added authorizer change triggers to `aws_api_gateway_deployment`:

```hcl
resource "aws_api_gateway_deployment" "this" {
  rest_api_id = aws_api_gateway_rest_api.project_apigateway.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_rest_api.project_apigateway.id,
      aws_api_gateway_authorizer.cognito.id,
      aws_api_gateway_authorizer.cognito.provider_arns,
      values(local.all_resources)[*].id,
      values(aws_api_gateway_method.methods)[*].id,
      values(aws_api_gateway_integration.integrations)[*].id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}
```

### Applied Changes

```bash
terraform plan
terraform apply
```

## Key Takeaways

- Recreating a Cognito User Pool invalidates **all existing JWTs** — users must sign in again
- API Gateway REST APIs require an **explicit redeployment** for authorizer changes to take effect — Terraform updating the authorizer alone is not enough
- Use `triggers` with a `sha1` hash on the deployment resource to automatically redeploy when authorizer or API config changes
- Always test the authorizer directly in the **AWS Console → API Gateway → Authorizers → Test** to isolate whether the issue is the token or the pipeline
