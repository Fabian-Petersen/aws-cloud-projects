# $ [Step 1] : IAM – Create Lambda Role
# -----------------------------
# IAM Role for Lambda
# -----------------------------
resource "aws_iam_role" "pdf_lambda_role" {
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
    Environment = var.env
  }
}

# $ [Step 2] : IAM – Create Lambda Permissions
# -----------------------------
# IAM Policy for Lambda
# -----------------------------
resource "aws_iam_role_policy" "pdf_lambda_policy" {
  role = aws_iam_role.pdf_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Read from DynamoDB tables (generated from list)
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          for table_name in var.dynamodb_table_names :
          "arn:aws:dynamodb:*:*:table/${table_name}"
        ]
      },
      # Streams Permissions (generated from list)
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetRecords",
          "dynamodb:GetShardIterator",
          "dynamodb:DescribeStream",
          "dynamodb:ListStreams"
        ]
        Resource = [
          for table_name in var.dynamodb_table_names :
          "arn:aws:dynamodb:*:*:table/${table_name}/stream/*"
        ]
      },
      # S3 access to write/read PDFs
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:PutObjectAcl",
          "s3:PutObjectTagging"
        ]
        Resource = "${var.s3_bucket_arn}/*"
      },

      # CloudWatch logging
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
# $ [Step 3] : IAM – Create Lambda Function
resource "aws_lambda_function" "pdf_generator" {
  function_name = var.function_name
  role          = aws_iam_role.pdf_lambda_role.arn
  package_type  = var.packageType
  image_uri     = var.image_uri
  # runtime       = var.runtime
  # handler       = var.lambda_handler
  timeout     = 30
  memory_size = 512

  tags = {
    Environment = var.env
  }
}

# $ [Step 4] : Connect the lambda and the dynamoDB supplying the stream.
resource "aws_lambda_event_source_mapping" "dynamoDB_to_lambda" {
  event_source_arn  = var.dynamodb_stream_arn
  function_name     = aws_lambda_function.pdf_generator.arn
  starting_position = "LATEST"
  batch_size        = 5
  enabled           = true
}


# $ [Step 5] : Attach a policy to the IAM role to allow cloudwatch logging
resource "aws_iam_role_policy_attachment" "pdf_lambda_logging" {
  role       = aws_iam_role.pdf_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
