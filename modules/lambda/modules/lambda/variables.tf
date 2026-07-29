variable "lambda_functions_custom" {
  type = map(object({
    file_name  = string
    handler    = string
    runtime    = string
    path       = optional(string)
    timeout    = optional(number, 15)
    invoked_by = optional(list(string), []) # e.g. ["apigateway", "s3", "eventbridge"]

    environment_variables = optional(map(string), {})
    scheduler_target      = optional(bool, false)      # true lets lambda publish to schedule group
    sns_publish_topics    = optional(list(string), []) # true lets lambda publish to sns

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

