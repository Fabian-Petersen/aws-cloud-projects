# output "dynamodb_table_name" {
#   description = "The name of the created DynamoDB table."
#   value       = aws_dynamodb_table.contactFormDB.name
# }

# output "dynamodb_table_arn" {
#   description = "The ARN of the created DynamoDB table."
#   value       = aws_dynamodb_table.contactFormDB.arn
# }

# output "vpc_endpoint_id" {
#   description = "The ID of the VPC endpoint for DynamoDB."
#   value       = aws_vpc_endpoint.dynamodb_endpoint.id
# }

output "dynamodb_stream_arns" {
  description = "Map of DynamoDB stream ARNs for tables with streams enabled"
  value = {
    for table_name, table_obj in aws_dynamodb_table.dynamodb_table :
    table_name => table_obj.stream_arn
    if var.dynamodb_tables[table_name].enable_stream
  }
}

# example dynamodb_stream_arns output {
#   "crud-nosql-app-maintenance-request-table" = "arn:aws:dynamodb:...:table/.../stream/..."
#   "crud-nosql-app-maintenance-action-table"  = "arn:aws:dynamodb:...:table/.../stream/..."
# }
