variable "lambda_functions" {
  type = map(object({
    file_name           = string
    handler             = string
    runtime             = string
    action              = list(string)
    dynamodb_table_name = string
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
