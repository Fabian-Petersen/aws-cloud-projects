resource "aws_dynamodb_table" "dynamodb_table" {
  for_each     = var.dynamodb_tables
  name         = "${each.key}-table"
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = each.value.pk
  range_key = lookup(each.value, "sk", null)

  dynamic "attribute" {
    for_each = distinct(compact(concat(
      [each.value.pk],
      [lookup(each.value, "sk", null)],
      each.value.enable_gsi ? [each.value.gsi.hash_key] : []
    )))
    content {
      name = attribute.value
      type = "S"
    }
  }
  dynamic "global_secondary_index" {
    for_each = each.value.enable_gsi ? [each.value.gsi] : []
    content {
      name            = global_secondary_index.value.name
      hash_key        = global_secondary_index.value.hash_key
      projection_type = global_secondary_index.value.projection
    }
  }

  stream_enabled   = each.value.enable_stream
  stream_view_type = each.value.enable_stream ? "NEW_AND_OLD_IMAGES" : null

  tags = {
    Env  = var.env
    Name = each.key
  }
}
