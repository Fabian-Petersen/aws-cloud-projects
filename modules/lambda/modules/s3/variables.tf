variable "file_name" { type = string }
variable "table_names" {
  type = list(string)
}
variable "bucket_name" {
  type = string
}
variable "handler" { type = string }
variable "lambda_name" { type = string }
