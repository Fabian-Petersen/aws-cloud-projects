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
    file_name  = string
    handler    = string
    runtime    = string
    path       = optional(string)
    invoked_by = optional(list(string), []) # e.g. ["apigateway", "s3", "eventbridge"]

    dynamodb_permissions = optional(map(object({
      table_name         = string
      actions            = list(string)
      allow_index_access = bool
    })), {})

    lambda_permissions = optional(map(object({
      function_name = string
      actions       = optional(list(string), ["lambda:InvokeFunction"])
    })), {})

    environment_variables = optional(map(string), {})
    scheduler_target      = optional(bool, false)

    statements = optional(list(object({
      sid       = optional(string)
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
