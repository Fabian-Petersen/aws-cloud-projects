variable "from_email" {
  type = string
} # for SES identity
variable "dynamodb_stream_arn" {
  type = string
} # trigger

variable "ses_filename" {}
# lambda packaging
variable "ses_function_name" {
  type = string
}

variable "ses_lambda_handler" {
  type = string
}

variable "runtime" {
  type = string
}

variable "ssm_param_arns" {
  type        = map(string)
  description = "parameters arns passed from the ssm module to the ses module"
}

variable "project_name" {}
variable "env" {}

variable "ssm_param_names" {}
