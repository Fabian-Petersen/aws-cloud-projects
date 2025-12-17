variable "lambda_functions" {
  type = map(object({
    file_name = string
    handler   = string
    runtime   = string
  }))
}
