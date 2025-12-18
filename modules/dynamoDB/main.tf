resource "aws_dynamodb_table" "dynamodb_table" {
  for_each     = toset(var.dynamoDB_table_names)
  name         = "${each.value}-table"
  billing_mode = "PAY_PER_REQUEST"

  hash_key = "id"

  attribute {
    name = "id"
    type = "S"
  }
  tags = {
    Env  = var.env
    Name = "${each.value}"
  }
}
