#$ Outputs for your frontend/backend
output "user_pool_id" {
  value = aws_cognito_user_pool.pool.id
}

output "client_id" {
  value = aws_cognito_user_pool_client.app_client.id
}

output "cognito_api_endpoint" {
  value = "https://cognito-idp.${var.region}.amazonaws.com/${aws_cognito_user_pool.pool.id}"
}