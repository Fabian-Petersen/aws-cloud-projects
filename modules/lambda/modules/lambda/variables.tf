variable "lambda_functions_custom" {
  type = map(object({
    file_name = string
    handler   = string
    runtime   = string
    timeout   = optional(number, 15)

    environment_variables = optional(map(string), {})

    inline_policy_statements = optional(list(object({
      sid       = optional(string)
      effect    = optional(string, "Allow")
      actions   = list(string)
      resources = list(string)
    })), [])

    managed_policy_arns = optional(list(string), [])
  }))
}

variable "env" {}
variable "project_name" {}
