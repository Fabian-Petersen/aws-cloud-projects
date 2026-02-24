variable "lambda_names" {}

variable "dynamic_lambda_policies" {
  type = map(object({
    action   = map(list(string))
    resource = string
  }))
}

variable "lambda_policies" {
  description = "Reusable IAM policy statements for Lambda functions"
  type = map(object({
    actions   = list(string)
    resources = list(string)
    effect    = optional(string, "Allow")
  }))
}

# variable "lambda_functions" {
#   type = map(object({
#     file_name = string
#     handler   = string
#     runtime   = string

#     statements = list(object({
#       effect    = optional(string, "Allow")
#       actions   = list(string)
#       resources = list(string)
#     }))
#   }))
# }

variable "lambda_functions" {
  type = map(object({
    file_name   = string
    handler     = string
    runtime     = string
    permissions = optional(set(string), [])
    statements = optional(list(object({
      effect    = optional(string, "Allow")
      actions   = list(string)
      resources = list(string)
    })), [])
  }))
}
