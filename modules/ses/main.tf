#$ Zip the existing Lambda functions from /lambdas/<function_directory>
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.root}/lambdas/jobs-notify-admin/jobs-notify-admin.py"
  output_path = "${path.root}/lambdas/jobs-notify-admin/${replace("jobs-notify-admin.py", ".py", ".zip")}"
}

resource "aws_ses_email_identity" "from" {
  email = var.from_email
}

#$ [Step 1] : Create an IAM role for the Lambda function to execute operations on dynamoDB
resource "aws_iam_role" "lambda_exec_role" {
  name = "${var.ses_function_name}_exec_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

#$ [Step 2] : Create the policy : Get SSM Parameters, GetItem from DynamoDB & send email templete to SES

data "aws_iam_policy_document" "lambda_policy" {
  statement {
    effect    = "Allow"
    actions   = ["ssm:GetParameter", "ssm:GetParameters"]
    resources = values(var.ssm_param_arns)
  }

  statement {
    effect    = "Allow"
    actions   = ["ses:SendEmail", "ses:SendRawEmail"]
    resources = ["*"]
  }
  statement {
    effect = "Allow"
    actions = ["dynamodb:DescribeStream", "dynamodb:GetRecords", "dynamodb:GetShardIterator", "dynamodb:ListStreams"
    ]
    resources = [var.dynamodb_stream_arn]
  }

  statement {
    effect    = "Allow"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["*"]
  }
}

# Convert the policy to json
resource "aws_iam_policy" "lambda_ses_notify" {
  name   = "${var.ses_function_name}-policy"
  policy = data.aws_iam_policy_document.lambda_policy.json
}


resource "aws_iam_role_policy_attachment" "attach" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_ses_notify.arn
}

#$ [Step 3] : Create the lambda function
resource "aws_lambda_function" "lambda_function" {
  function_name = var.ses_function_name
  role          = aws_iam_role.lambda_exec_role.arn
  filename      = var.ses_filename
  handler       = var.ses_lambda_handler
  runtime       = var.runtime

  environment {
    variables = {
      SSM_PARAMS_JSON = jsonencode(var.ssm_param_names)
      SES_FROM_EMAIL  = var.from_email
    }
  }
}

#$ [Step 4] : Invoke the lambda with dynamoDB streams
resource "aws_lambda_event_source_mapping" "dynamoDB_to_lambda" {
  event_source_arn  = var.dynamodb_stream_arn
  function_name     = aws_lambda_function.lambda_function.arn
  starting_position = "LATEST"
  batch_size        = 5
  enabled           = true
}
