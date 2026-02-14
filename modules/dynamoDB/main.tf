resource "aws_dynamodb_table" "dynamodb_table" {
  # for_each     = toset(var.dynamoDB_table_names)
  for_each     = var.dynamodb_tables
  name         = "${each.key}-table"
  billing_mode = "PAY_PER_REQUEST"

  hash_key = "id"

  # Standard attributes
  attribute {
    name = "id"
    type = "S"
  }

  # $ GSI attribute
  dynamic "attribute" {
    for_each = each.value.enable_gsi ? [
      { name = each.value.gsi.hash_key, type = "S" }
    ] : []
    content {
      name = attribute.value.name
      type = attribute.value.type
    }
  }

  # $ GSI itself
  dynamic "global_secondary_index" {
    for_each = each.value.enable_gsi ? [each.value.gsi] : []
    content {
      name            = global_secondary_index.value.name
      hash_key        = global_secondary_index.value.hash_key
      projection_type = global_secondary_index.value.projection
    }
  }

  # $ Streams
  stream_enabled   = each.value.enable_stream
  stream_view_type = each.value.enable_stream ? "NEW_AND_OLD_IMAGES" : null
  tags = {
    Env  = var.env
    Name = "${each.key}"
  }
}
