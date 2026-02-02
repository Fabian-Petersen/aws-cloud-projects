output "lambda_invoke_arn" {
  description = "arn for the pdf generator lambda"
  value       = aws_lambda_function.pdf_generator.arn
}

output "lambda_name" {
  description = "name of the pdf generator lambda"
  value       = aws_lambda_function.pdf_generator.name
}
