variable "project_name" {
  type        = string
  description = "Project name prefix"
}

variable "environment" {
  type = string
}

variable "dynamodb_table_name" {
  type = string
}

variable "lambda_zip_path" {
  type        = string
  description = "Path to lambda zip file"
}

variable "lambda_handler" {
  type    = string
  default = "handler.lambda_handler"
}

variable "runtime" {
  type = string
}

variable "s3_bucket" {
  type = string
}
