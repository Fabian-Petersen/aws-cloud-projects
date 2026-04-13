# variable "lambda_functions" {
#   description = "lambda functions required for backend"
#   type = map(object({
#     file_name           = string
#     handler             = string
#     runtime             = string
#     action              = list(string)
#     dynamodb_table_name = string
#     allow_index_access  = bool
#     # permissions         = set(string) # Add permission with dynamic IAM Roles
#   }))
# }

variable "env" {}
variable "project_name" {}

variable "lambda_functions" {
  type = map(object({
    file_name = string
    handler   = string
    runtime   = string

    dynamodb_permissions = map(object({
      table_name         = string
      actions            = list(string)
      allow_index_access = bool
    }))

    statements = optional(list(object({
      effect    = optional(string, "Allow")
      actions   = list(string)
      resources = list(string)

      conditions = optional(list(object({
        test     = string
        variable = string
        values   = list(string)
      })), [])
    })), [])
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
