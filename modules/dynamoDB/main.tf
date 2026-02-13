resource "aws_dynamodb_table" "dynamodb_table" {
  for_each     = toset(var.dynamoDB_table_names)
  name         = "${each.value}-table"
  billing_mode = "PAY_PER_REQUEST"

  hash_key = "id"

# Standard attributes
  attribute {
    name = "id"
    type = "S"
  }

  # Conditionally add GSI if this table is in table_gsi_map
  dynamic "attribute" {
    for_each = lookup(var.table_gsi_map, each.value, null) == null ? [] : [
      { name = var.table_gsi_map[each.value].hash_key, type = "S" }
    ]
    content {
      name = attribute.value.name
      type = attribute.value.type
    }
  }

  dynamic "global_secondary_index" {
    for_each = lookup(var.table_gsi_map, each.value, null) == null ? [] : [var.table_gsi_map[each.value]]
    content {
      name            = global_secondary_index.value.name
      hash_key        = global_secondary_index.value.hash_key
      projection_type = global_secondary_index.value.projection
    }
  }

  tags = {
    Env  = var.env
    Name = "${each.value}"
  }
}