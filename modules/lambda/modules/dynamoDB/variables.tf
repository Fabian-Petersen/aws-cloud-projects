variable "lambda_functions" {
  description = "lambda functions required for backend"
  type = map(object({
    file_name           = string
    handler             = string
    runtime             = string
    action              = list(string)
    dynamodb_table_name = string
    allow_index_access  = bool
    # permissions         = set(string) # Add permission with dynamic IAM Roles
  }))
}
variable "region" {
  description = "aws region for the project"
  type        = string
}

variable "profile_2_account_id" {
  description = "free tier account id"
  type        = string
}

variable "extra_policies" {
  description = "Optional map of extra IAM policy ARNs per Lambda"
  type        = map(string)
}
