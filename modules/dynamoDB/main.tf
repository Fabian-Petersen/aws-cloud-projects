resource "aws_dynamodb_table" "contactFormDB" {
  name = "portfolio_contacts_database"
  # billing_mode = "PAY_PER_REQUEST"

  hash_key = "id"

  attribute {
    name = "id"
    type = "S"
  }
}

# resource "aws_vpc_endpoint" "dynamodb_endpoint" {
#   vpc_id          = var.vpc_id
#   service_name    = "com.amazonaws.${var.region}.dynamodb"
#   route_table_ids = var.route_table_ids

# tags = {
#   Name = "contactFormDB_vpc_endpoint"
# }
# }