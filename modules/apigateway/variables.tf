variable "project_name" {
  description = "The name of the project"
  type        = string
}

variable "env" {
  description = "development environment"
  type        = string
}

# variable "resource_path" {
#   description = "The name of the path of the api e.g. /bookings or /users/{id}"
#   type        = string
# }

variable "api_name" {
  description = "Name of the api for the project"
  type        = string
}
variable "api_parent_routes" {
  type = map(object({
    methods = optional(map(object({
      lambda        = string
      authorization = string
    })), {}) # default empty map
  }))
  default = {}
}


variable "api_child_routes" {
  type = map(object({
    parent_key = string
    path_part  = string
    methods = map(object({
      lambda        = string
      authorization = string
    }))
  }))
}



#$ ============== Add the lambda functions to integrate with the api ===================
variable "lambda_functions" {
  description = "lambda functions required for backend"
  type = map(object({
    file_name           = string
    handler             = string
    runtime             = string
    action              = list(string)
    dynamodb_table_name = string
  }))
}

variable "cognito_arn" {}

variable "lambda_arns" {
  description = "arn values for each lambda function passed to the api for integration"
  type        = map(string)
}
