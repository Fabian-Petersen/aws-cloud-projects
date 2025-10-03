#$ [Step 1] : Zip the existing Lambda functions from /lambdas
data "archive_file" "lambda_zip" {
  for_each = var.lambda_functions
  type        = "zip"
  source_file = "${path.root}/lambdas/${each.value.file_name}"
  output_path = "${path.root}/lambdas/${replace(each.value.file_name, ".py", ".zip")}"
}

#$ [Step 1] : Create an IAM role for the Lambda function
resource "aws_iam_role" "lambda_exec_role" {
  for_each = var.lambda_functions
  name     = "${each.key}_exec_role"

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

#$ [Step 2] : Attach a policy to the IAM role to allow logging
resource "aws_iam_role_policy_attachment" "lambda_logging" {
  for_each   = var.lambda_functions
  role       = aws_iam_role.lambda_exec_role[each.key].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

#$ [Step 3] : Create the Lambda function
resource "aws_lambda_function" "lambda_function" {
  for_each      = var.lambda_functions

  function_name = each.key
  role          = aws_iam_role.lambda_exec_role[each.key].arn
  handler       = each.value.handler # <filename>.<function_name>
  runtime       = each.value.runtime                          # preferred runtime e.g. python3.9
  filename      = data.archive_file.lambda_zip[each.key].output_path
  source_code_hash = data.archive_file.lambda_zip[each.key].output_base64sha256

  #% [INFO] The hash updates when code changes and terraform will update the code in the cloud
  timeout       = 15
}