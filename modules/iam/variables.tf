# variable "lambda_names" {}

# variable "dynamic_lambda_policies" {
#   type = map(object({
#     action   = map(list(string))
#     resource = string
#   }))
# }

# variable "lambda_policies" {
#   description = "Reusable IAM policy statements for Lambda functions"
#   type = map(object({
#     actions   = list(string)
#     resources = list(string)
#     effect    = optional(string, "Allow")
#   }))
# }

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

variable "lambda_role_names" {
  description = "Map of lambda function keys to their execution role names"
  type        = map(string)
}
