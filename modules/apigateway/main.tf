
#$ [Step 1] : Define the API for the project
resource "aws_api_gateway_rest_api" "project_apigateway" {
  name        = "${var.project_name}-apigateway"
  description = "API for ${var.project_name}"
}

#$ [Step 2] : Define the Resources e.g. bookings & users
resource "aws_api_gateway_resource" "resources" {
  for_each    = var.api_routes
  rest_api_id = aws_api_gateway_rest_api.project_apigateway.id
  parent_id   = aws_api_gateway_rest_api.project_apigateway.root_resource_id
  path_part   = each.key
}

locals {
  method_map = flatten([
    for resource_name, route in var.api_routes : [
      for method, lambda in route.methods : {
        resource_name = resource_name
        http_method   = method
        lambda_name   = lambda
      }
    ]
  ])
}

#$ [Step 3] : Define the Methods (look through the api routes variable)
resource "aws_api_gateway_method" "methods" {
  for_each = {
    for m in local.method_map :
    "${m.resource_name}_${m.http_method}" => m
  }

  rest_api_id   = aws_api_gateway_rest_api.project_apigateway.id
  resource_id   = aws_api_gateway_resource.resources[each.value.resource_name].id
  http_method   = each.value.http_method
  authorization = "NONE"
}

#$ [Step 4] : Integrate with the backend e.g. lambda functions, HTTP endpoints or AWS Services
resource "aws_api_gateway_integration" "integrations" {
  for_each = {
    for m in local.method_map :
    "${m.resource_name}_${m.http_method}" => m
  }

  rest_api_id             = aws_api_gateway_rest_api.project_apigateway.id
  resource_id             = aws_api_gateway_resource.resources[each.value.resource_name].id
  http_method             = each.value.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.lambda_arns[each.value.lambda_name] # ARN of the lambda function
}

#$ [Step 5] : Deploy the API
resource "aws_api_gateway_deployment" "deploy_api" {
  rest_api_id = aws_api_gateway_rest_api.project_apigateway.id

  #% [INFO] : Trigger redeployment on changes to resources or methods
  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_rest_api.project_apigateway.id,
      values(aws_api_gateway_resource.resources)[*].id,
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

#$ [Step 6] : Set API Permissions to invoke lambda functions / services
resource "aws_lambda_permission" "allow_api_gateway" {
  for_each      = var.lambda_functions
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = each.key
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.project_apigateway.execution_arn}/*/*"
}

# aws_lambda_function.methods_lambda.invoke_arn # ARN of the lambda function
#$ [Step 7] : Set the deployment Stage

