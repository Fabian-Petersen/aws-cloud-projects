# $ This lambda is invoked when an image is uploaded to the s3 bucket for /assets or /maintenance and store the metadata in dynamoDB for /assets and /maintenance

#$ [Step 1] : Zip the existing Lambda functions from /lambdas/<function_directory>
data "archive_file" "lambda_zip" {
  type = "zip"
  #   source_file = "${path.root}/lambdas/${each.key}/${each.value.file_name}"
  source_file = "${path.root}/lambdas/${var.lambda_name}/${var.file_name}"
  output_path = "${path.root}/lambdas/${var.lambda_name}/${replace(var.file_name, ".py", ".zip")}"
}

# $ s3 bucket already exist
data "aws_s3_bucket" "bucket" {
  bucket = var.bucket_name
}

data "aws_dynamodb_table" "tables" {
  for_each = toset(var.table_names)
  name     = each.value
}

resource "aws_iam_role" "lambda_role" {
  name = "${var.lambda_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_policy" "lambda_policy" {
  name = "${var.lambda_name}-lambda-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # DynamoDB
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:UpdateItem"
        ]
        Resource = [
          for t in values(data.aws_dynamodb_table.tables) : t.arn
        ]
      },
      # S3
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Resource = [
          "${data.aws_s3_bucket.bucket.arn}/maintenance/*",
        "${data.aws_s3_bucket.bucket.arn}/assets/*"]
      },
      # Logs
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

resource "aws_iam_role_policy_attachment" "lambda_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

resource "aws_lambda_function" "s3_event_lambda" {
  function_name    = var.lambda_name
  role             = aws_iam_role.lambda_role.arn
  runtime          = "python3.14"
  handler          = var.handler
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
}

resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.s3_event_lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = data.aws_s3_bucket.bucket.arn
}

resource "aws_s3_bucket_notification" "s3_notification" {
  bucket = data.aws_s3_bucket.bucket.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.s3_event_lambda.arn
    events              = ["s3:ObjectCreated:Put"]
    filter_prefix       = "maintenance/" // files that are placed in this directory will trigger the lambda "/maintenance/{image_id}/20251211_5153446"  
  }


  lambda_function {
    lambda_function_arn = aws_lambda_function.s3_event_lambda.arn
    events              = ["s3:ObjectCreated:Put"]
    filter_prefix       = "assets/"
  }

  depends_on = [aws_lambda_permission.allow_s3]
}
