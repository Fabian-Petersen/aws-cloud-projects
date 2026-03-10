output "custom_lambda_invoke_arns" {
  description = "A map of all the lambda arn's created in the module"
  value = {
    for k, v in aws_lambda_function.lambda_function :
    k => v.invoke_arn
  }
}
