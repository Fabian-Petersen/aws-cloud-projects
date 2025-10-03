variable "project_name" {
  default     = "uwc-booking-app"
  description = "The name of the project"
  type        = string
}

variable "env" {
  default     = "env"
  description = "development environment"
  type        = string
}

# variable "resource_path" {
#   description = "The name of the path of the api e.g. /bookings or /users/{id}"
#   type        = string
# }

variable "api_name" {
  default     = "project_apigateway"
  description = "Name of the api for the project"
  type        = string
}

variable "api_routes" {
  type = map(object({
    methods = map(string) # method => lambda_function_name
  }))
  default = {
    bookings = {
      methods = {
        GET  = "getBookings_lambda"
        POST = "postBooking_lambda"
      }
    }
    users = {
      methods = {
        GET = "getUsers_lambda"
      }
    }
  }
}

#$ ============== Add the lambda functions to integrate with the api ===================
variable "lambda_functions" {
  type = map(object({
    file_name = string
    handler   = string
    runtime   = string
  }))
  default = {
    getBookings_lambda = {
      file_name = "/lambdas/getBooking_lambda.py"
      handler   = "getBooking_lambda.handler"
      runtime   = "python3.9"
    }
    postBooking_lambda = {
      file_name = "/lambdas/postBooking_lambda.py"
      handler   = "postBooking_lambda.handler"
      runtime   = "python3.9"
    }
    getUsers_lambda = {
      file_name = "/lambdas/getUsers_lambda.py"
      handler   = "getUsers_lambda.handler"
      runtime   = "python3.9"
    }
  }
}

variable "lambda_arns" {
  description = "arn values for each lambda function passed to the api for integration"
  type        = map(string)
}

variable "lambda_function_names" {
  type = map(string)
}