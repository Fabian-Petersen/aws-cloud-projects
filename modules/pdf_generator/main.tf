# $ Create a Lambda
resource "aws_lambda_function" "pdf_generator" {
  function_name = "${var.project_name}-pdf-generator"
  role          = aws_iam_role.lambda_role.arn
  runtime       = var.runtime
  handler       = var.lambda_handler
  filename      = var.lambda_zip_path
  timeout       = 30
  memory_size   = 512

  environment {
    variables = {
      TABLE_NAME = var.dynamodb_table_name
      BUCKET     = var.s3_bucket
    }
  }

  tags = {
    Environment = var.environment
  }
}

# $ IAM – Lambda Permissions
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-pdf-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = {
    Environment = var.environment
  }
}

resource "aws_iam_role_policy" "lambda_policy" {
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem"
        ]
        Resource = "arn:aws:dynamodb:*:*:table/${var.dynamodb_table_name}"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Resource = "${var.s3_bucket}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

#$ [Step 3] : Attach a policy to the IAM role to allow cloudwatch logging
resource "aws_iam_role_policy_attachment" "lambda_logging" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
