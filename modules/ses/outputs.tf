output "ses_from_identity_email" {
  value = aws_ses_email_identity.from.email
}

output "lambda_policy_arn" {
  value = aws_iam_policy.lambda_ses_notify.arn
}
