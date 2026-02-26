output "ssm_param_names" {
  value = { for k, v in aws_ssm_parameter.this : k => v.name }
}

output "ssm_param_arns" {
  value = { for k, v in aws_ssm_parameter.this : k => v.arn }
}
