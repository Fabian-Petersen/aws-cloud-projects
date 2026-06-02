variable "project_name" {
  description = "The name of the project"
  type        = string
}


variable "region" {
  description = "aws region for the project"
  type        = string
}

variable "env" {
  description = "development environment: dev, staging or prod"
  type        = string
}

variable "dynamodb_tables" {
  type = map(object({
    enable_gsi    = bool
    enable_stream = bool
    stream_filter = optional(list(string), ["INSERT"])

    # Per-table primary key config
    pk = optional(string) # default "id" if not set
    sk = optional(string) # only set if you want a sort key

    gsis = optional(map(object({
      hash_key           = string
      range_key          = optional(string)
      projection_type    = string
      non_key_attributes = optional(list(string))
    })))
  }))
}

variable "event_subscriptions" {
  type = map(object({
    source      = string
    detail_type = string
    targets = list(object({
      name        = string
      target_type = string
    }))
  }))
}

variable "resource_permissions" {
  description = "Generic list of resource permissions for EventBridge targets"
  type = list(object({
    service     = string # "lambda", "sqs", etc.
    principal   = string # "events.amazonaws.com"
    target_name = string # must match the name in event_subscriptions targets
    target_arn  = string # ARN of the resource being invoked (e.g. Lambda ARN)
    source_arn  = string # ARN of the EventBridge rule granting permission
  }))
  default = []
}

variable "dynamodb_stream_arns" {
  description = "Map of table name => stream ARN, from the dynamodb module output"
  type        = map(string)
}
