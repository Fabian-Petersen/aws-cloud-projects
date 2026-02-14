variable "project_name" {
  type        = string
  description = "Project name prefix"
}

variable "env" {
  type = string
}

variable "dynamodb_table_names" {
  type = list(string)
}

variable "image_uri" {}
# variable "lambda_zip_path" {
#   type        = string
#   description = "Path to lambda zip file"
# }

variable "packageType" {
  type        = string
  description = "Package to upload lambda (zip / image)"
}

variable "function_name" {}

# variable "lambda_handler" {
#   type    = string
#   default = "handler.lambda_handler"
# }

# variable "runtime" {
#   type = string
# }

variable "s3_bucket_arn" {
  type = string
}

variable "dynamodb_stream_arn" {
  type = string
}
