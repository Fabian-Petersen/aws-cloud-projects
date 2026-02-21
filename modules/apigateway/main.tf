
#$ [Step 1] : Define the API for the project
resource "aws_api_gateway_rest_api" "project_apigateway" {
  name        = "${var.project_name}-apigateway"
  description = "API for ${var.project_name}"
}

#$ [Step 2] : Parent Resources
resource "aws_api_gateway_resource" "parents" {
  for_each    = var.api_parent_routes
  rest_api_id = aws_api_gateway_rest_api.project_apigateway.id
  parent_id   = aws_api_gateway_rest_api.project_apigateway.root_resource_id
  path_part   = each.key
}


#$ [Step 3] : Child Resources
resource "aws_api_gateway_resource" "children" {
  for_each    = var.api_child_routes
  rest_api_id = aws_api_gateway_rest_api.project_apigateway.id
  parent_id   = aws_api_gateway_resource.parents[each.value.parent_key].id
  path_part   = each.value.path_part
}

#$ [Step 4] : Methods Map
locals {
  all_routes = merge(
    { for k, v in var.api_parent_routes : k => v },
    { for k, v in var.api_child_routes : k => v }
  )

  # $ This is used to flatten the object when the variable is a nested object method = {GET = {
  # $ lambda = "function-name", ""}

  method_map = flatten([
    for key, route in local.all_routes : [
      for method, info in route.methods : { # rename lambda -> info
        resource_name = key
        http_method   = method
        lambda_name   = info.lambda
        authorization = info.authorization
      }
    ]
  ])
}

#$ [Step 5] : Methods
resource "aws_api_gateway_method" "methods" {
  for_each = {
    for m in local.method_map :
    "${m.resource_name}_${m.http_method}" => m
  }

  rest_api_id   = aws_api_gateway_rest_api.project_apigateway.id
  resource_id   = lookup(aws_api_gateway_resource.parents, each.value.resource_name, null) != null ? aws_api_gateway_resource.parents[each.value.resource_name].id : aws_api_gateway_resource.children[each.value.resource_name].id
  http_method   = each.value.http_method
  authorization = each.value.authorization == "NONE" ? "NONE" : "COGNITO_USER_POOLS" # use authorization from locals
  # authorizer_id = aws_api_gateway_authorizer.cognito.id
  authorizer_id = each.value.authorization == "COGNITO_USER_POOLS" ? aws_api_gateway_authorizer.cognito.id : null
}

#$ [Step 6]: Integrations
resource "aws_api_gateway_integration" "integrations" {
  for_each = {
    for m in local.method_map :
    "${m.resource_name}_${m.http_method}" => m
  }

  rest_api_id             = aws_api_gateway_rest_api.project_apigateway.id
  resource_id             = lookup(aws_api_gateway_resource.parents, each.value.resource_name, null) != null ? aws_api_gateway_resource.parents[each.value.resource_name].id : aws_api_gateway_resource.children[each.value.resource_name].id
  http_method             = each.value.http_method
  integration_http_method = each.value.http_method == "OPTIONS" ? null : "POST"
  type                    = each.value.http_method == "OPTIONS" ? "MOCK" : "AWS_PROXY"
  uri                     = each.value.http_method == "OPTIONS" ? null : var.lambda_arns[each.value.lambda_name]

  request_templates = each.value.http_method == "OPTIONS" ? {
    "application/json" = "{\"statusCode\": 200}"
  } : null

  depends_on = [
    aws_api_gateway_method.methods
  ]
}

# Method Response for OPTIONS
resource "aws_api_gateway_method_response" "options_response" {
  for_each = {
    for m in local.method_map :
    "${m.resource_name}_${m.http_method}" => m
    if m.http_method == "OPTIONS" # $ <-- Only executed on the OPTIONS methods defined here
  }
  rest_api_id = aws_api_gateway_rest_api.project_apigateway.id
  resource_id = lookup(aws_api_gateway_resource.parents, each.value.resource_name, null) != null ? aws_api_gateway_resource.parents[each.value.resource_name].id : aws_api_gateway_resource.children[each.value.resource_name].id
  http_method = each.value.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers"     = true
    "method.response.header.Access-Control-Allow-Methods"     = true
    "method.response.header.Access-Control-Allow-Origin"      = true
    "method.response.header.Access-Control-Allow-Credentials" = true # check if this will break the CORS
  }
  depends_on = [aws_api_gateway_method.methods]
}

# $ Integration Response for OPTIONS
resource "aws_api_gateway_integration_response" "options_integration_response" {
  for_each = {
    for m in local.method_map :
    "${m.resource_name}_${m.http_method}" => m
    if m.http_method == "OPTIONS" # $ <-- Only executed on the OPTIONS methods defined here
  }

  rest_api_id = aws_api_gateway_rest_api.project_apigateway.id
  resource_id = lookup(aws_api_gateway_resource.parents, each.value.resource_name, null) != null ? aws_api_gateway_resource.parents[each.value.resource_name].id : aws_api_gateway_resource.children[each.value.resource_name].id
  http_method = each.value.http_method
  status_code = aws_api_gateway_method_response.options_response[each.key].status_code

  response_parameters = {
    # "method.response.header.Access-Control-Allow-Origin"  = "'https://${var.subdomain_name}'"
    "method.response.header.Access-Control-Allow-Origin"      = "'http://localhost:5173'"
    "method.response.header.Access-Control-Allow-Headers"     = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods"     = "'GET,POST,OPTIONS,PUT,DELETE'"
    "method.response.header.Access-Control-Allow-Credentials" = "'true'"
  }
  response_templates = {
    "application/json" = "{}"
  }
  depends_on = [aws_api_gateway_integration.integrations]
}


# Set the Gateway Responses when using a "Authorizer"
resource "aws_api_gateway_gateway_response" "default_4xx" {
  rest_api_id   = aws_api_gateway_rest_api.project_apigateway.id
  response_type = "DEFAULT_4XX"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin"      = "'https://${var.subdomain_name}'"
    "gatewayresponse.header.Access-Control-Allow-Headers"     = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "gatewayresponse.header.Access-Control-Allow-Methods"     = "'GET,POST,OPTIONS,PUT,DELETE'"
    "gatewayresponse.header.Access-Control-Allow-Credentials" = "'true'"
  }
}

resource "aws_api_gateway_gateway_response" "default_5xx" {
  rest_api_id   = aws_api_gateway_rest_api.project_apigateway.id
  response_type = "DEFAULT_5XX"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin"      = "'https://${var.subdomain_name}'"
    "gatewayresponse.header.Access-Control-Allow-Headers"     = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "gatewayresponse.header.Access-Control-Allow-Methods"     = "'GET,POST,OPTIONS,PUT,DELETE'"
    "gatewayresponse.header.Access-Control-Allow-Credentials" = "'true'"
  }
}

#$ [Step 6]: Cognito Authorisation
resource "aws_api_gateway_authorizer" "cognito" {
  name            = "CognitoAuthorizer"
  rest_api_id     = aws_api_gateway_rest_api.project_apigateway.id
  identity_source = "method.request.header.Authorization"
  type            = "COGNITO_USER_POOLS"
  provider_arns   = [var.cognito_arn]
}

#$ [Step 7]: Deployment & Stage
resource "aws_api_gateway_deployment" "deploy_api" {
  rest_api_id = aws_api_gateway_rest_api.project_apigateway.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_rest_api.project_apigateway.id,
      values(aws_api_gateway_resource.parents)[*].id,
      values(aws_api_gateway_resource.children)[*].id,
      values(aws_api_gateway_method.methods)[*].id,
      values(aws_api_gateway_integration.integrations)[*].id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [aws_api_gateway_integration.integrations]
}

resource "aws_api_gateway_stage" "deployment_stage" {
  deployment_id = aws_api_gateway_deployment.deploy_api.id
  rest_api_id   = aws_api_gateway_rest_api.project_apigateway.id
  stage_name    = var.env
}

#$ [Step 8] : Set API Permissions to invoke lambda functions / services
resource "aws_lambda_permission" "allow_api_gateway" {
  for_each      = var.lambda_functions
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = each.key
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.project_apigateway.execution_arn}/*/*"
}
