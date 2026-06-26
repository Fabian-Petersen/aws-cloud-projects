output "custom_lambda_invoke_arns" {
  description = "A map of all the lambda arn's created in the module"
  value = {
    for k, v in aws_lambda_function.lambda_function :
    k => v.invoke_arn
  }
}

output "custom_lambda_arns" {
  value = {
    for k, v in aws_lambda_function.lambda_function :
    k => v.arn
  }
}

# $ Return map of lambdas that publish to SNS topic
output "allowed_lambda_arns" {
  value = {
    for k, v in aws_lambda_function.lambda_function :
    k => v.arn
    if try(var.lambda_functions_custom[k].publish_sns, false)
  }
}
