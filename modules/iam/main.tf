data "aws_iam_policy_document" "lambda" {
  for_each = var.lambda_functions

  # Base logs (optional but recommended)
  statement {
    effect    = "Allow"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["*"]
  }

  # Feature bundles
  dynamic "statement" {
    for_each = {
      for k, v in var.lambda_policies :
      k => v
      if contains(tolist(each.value.features), k)
    }

    content {
      effect    = try(statement.value.effect, "Allow")
      actions   = statement.value.actions
      resources = statement.value.resources
    }
  }

  # Per-lambda custom statements (optional)
  dynamic "statement" {
    for_each = try(each.value.statements, [])
    content {
      effect    = try(statement.value.effect, "Allow")
      actions   = statement.value.actions
      resources = statement.value.resources
    }
  }
}

resource "aws_iam_role" "lambda" {
  for_each = var.lambda_functions
  name     = "${each.key}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_policy" "lambda" {
  for_each = var.lambda_functions
  name     = "${each.key}-lambda-policy"
  policy   = data.aws_iam_policy_document.lambda[each.key].json
}

resource "aws_iam_role_policy_attachment" "lambda" {
  for_each   = var.lambda_functions
  role       = aws_iam_role.lambda[each.key].name
  policy_arn = aws_iam_policy.lambda[each.key].arn
}

# // Use document instead of jsonencode to make it abit easier and convert to json later
# data "aws_iam_policy_document" "lambda" {
#   for_each = var.lambda_functions

#   # Optional: always include logs (recommended)
#   statement {
#     effect    = "Allow"
#     actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
#     resources = ["*"]
#   }

#   dynamic "statement" {
#     for_each = {
#       for k, v in var.lambda_policies :
#       k => v
#       if contains(tolist(try(each.value.permissions, [])), k)
#     }

#     content {
#       effect    = try(statement.value.effect, "Allow")
#       actions   = statement.value.actions
#       resources = statement.value.resources
#     }
#   }

#   dynamic "statement" {
#     for_each = try(each.value.extra_statements, [])
#     content {
#       effect    = try(statement.value.effect, "Allow")
#       actions   = statement.value.actions
#       resources = statement.value.resources
#     }
#   }
# }
