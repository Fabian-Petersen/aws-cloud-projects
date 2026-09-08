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
    include_shared_utils  = optional(bool, false)

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

# $ Lambdas not tied to the dynamoDB routes, these lambdas use custom policies as needed
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
    include_shared_utils  = optional(bool, false)

    inline_policy_statements = optional(list(object({
      sid       = optional(string)
      effect    = optional(string, "Allow")
      actions   = list(string)
      resources = list(string)
    })), [])

    managed_policy_arns = optional(list(string), [])
  }))
}
