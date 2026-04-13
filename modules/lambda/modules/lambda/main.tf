# $ This module creates a lambda function with its own custom policy.
#$ [Step 1] : Zip the existing Lambda functions from /lambdas/<function_directory>
data "archive_file" "lambda_zip" {
  for_each    = var.lambda_functions_custom
  type        = "zip"
  source_file = "${path.root}/lambdas/${each.key}/${each.value.file_name}"
  output_path = "${path.root}/lambdas/${each.key}/${replace(each.value.file_name, ".py", ".zip")}"
}

#$ [Step 1] : Create an IAM role for the Lambda function to execute operations on dynamoDB
resource "aws_iam_role" "lambda_exec_role" {
  for_each = var.lambda_functions_custom
  name     = "${each.key}_exec_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}
#$ [Step 2] : Create the policy that define scope of lambda access to dynamoDB table
resource "aws_iam_role_policy" "inline_policy" {
  for_each = {
    for k, v in var.lambda_functions_custom :
    k => v
    if length(v.inline_policy_statements) > 0
  }

  name = "${each.key}_inline_policy"
  role = aws_iam_role.lambda_exec_role[each.key].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      for stmt in each.value.inline_policy_statements : {
        Sid      = try(stmt.sid, null)
        Effect   = try(stmt.effect, "Allow")
        Action   = stmt.actions
        Resource = stmt.resources
      }
    ]
  })
}

locals {
  managed_policy_attachments = flatten([
    for lambda_name, lambda in var.lambda_functions_custom : [
      for policy_arn in lambda.managed_policy_arns : {
        lambda_name = lambda_name
        policy_arn  = policy_arn
      }
    ]
  ])
}

resource "aws_iam_role_policy_attachment" "managed_policies" {
  for_each = {
    for item in local.managed_policy_attachments :
    "${item.lambda_name}-${replace(item.policy_arn, ":", "_")}" => item
  }

  role       = aws_iam_role.lambda_exec_role[each.value.lambda_name].name
  policy_arn = each.value.policy_arn
}


#$ [Step 3] : Attach a policy to the IAM role to allow cloudwatch logging
resource "aws_iam_role_policy_attachment" "lambda_logging" {
  for_each   = var.lambda_functions_custom
  role       = aws_iam_role.lambda_exec_role[each.key].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

#$ [Step 3.1] : Create CloudWatch Log Group with 3-day retention for each Lambda
resource "aws_cloudwatch_log_group" "lambda_log_group" {
  for_each = var.lambda_functions_custom

  name              = "/aws/lambda/${each.key}"
  retention_in_days = 3

  tags = {
    Name        = "${var.project_name}_cloudwatch_logs"
    Environment = var.env
  }
}

#$ [Step 4] : Create the Lambda function
resource "aws_lambda_function" "lambda_function" {
  for_each = var.lambda_functions_custom

  environment {
    variables = each.value.environment_variables
  }

  function_name    = each.key
  role             = aws_iam_role.lambda_exec_role[each.key].arn
  handler          = each.value.handler
  runtime          = each.value.runtime
  filename         = data.archive_file.lambda_zip[each.key].output_path
  source_code_hash = data.archive_file.lambda_zip[each.key].output_base64sha256
  timeout          = each.value.timeout

  depends_on = [
    aws_cloudwatch_log_group.lambda_log_group,
    aws_iam_role_policy_attachment.lambda_logging
  ]

  tags = {
    Name        = "${var.project_name}/${each.key}"
    Environment = var.env
  }
}

