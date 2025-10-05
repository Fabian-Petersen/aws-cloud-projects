variable "lambda_functions" {
  type = map(object({
    file_name = string
    handler   = string
    runtime   = string
  }))
  default = {
    getBookings_lambda = {
      file_name = "getBooking_lambda.py"
      handler   = "getBooking_lambda.handler"
      runtime   = "python3.9"
    }
    postBooking_lambda = {
      file_name = "postBooking_lambda.py"
      handler   = "postBooking_lambda.handler"
      runtime   = "python3.9"
    }
    getUsers_lambda = {
      file_name = "getUsers_lambda.py"
      handler   = "getUsers_lambda.handler"
      runtime   = "python3.9"
    }
  }
}

variable "region" {

}

variable "profile_2_account_id" {
  # default     = "157489943321"
  description = "free tier account id"
  type        = string
}