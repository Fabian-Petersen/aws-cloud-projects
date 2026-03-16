# $ This module create an additional policy statement for lambda functions using the statements additional block in the variable. 

#$ Filter the lambda_functions variable and return only lambda functions with statements block added
locals {
  lambda_functions_with_statements = {
    for k, v in var.lambda_functions :
    k => v
    if try(length(v.statements), 0) > 0
  }
}

data "aws_iam_policy_document" "lambda" {
  for_each = local.lambda_functions_with_statements

  # Only add this if their are no logs policies attached. In crud-nosql project this is created with the lambda itself
  # statement {
  #   effect    = "Allow"
  #   actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
  #   resources = ["*"]
  # }

  # Per-lambda custom statements
  dynamic "statement" {
    for_each = try(each.value.statements, [])
    content {
      effect    = try(statement.value.effect, "Allow")
      actions   = statement.value.actions
      resources = statement.value.resources

      dynamic "condition" {
        for_each = try(statement.value.conditions, [])
        content {
          test     = condition.value.test
          variable = condition.value.variable
          values   = condition.value.values
        }
      }
    }
  }
}

resource "aws_iam_policy" "lambda" {
  for_each = local.lambda_functions_with_statements
  name     = "${each.key}-lambda-policy"
  policy   = data.aws_iam_policy_document.lambda[each.key].json
}

resource "aws_iam_role_policy_attachment" "lambda" {
  for_each   = local.lambda_functions_with_statements
  role       = var.lambda_role_names[each.key]
  policy_arn = aws_iam_policy.lambda[each.key].arn
}
