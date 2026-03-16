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
