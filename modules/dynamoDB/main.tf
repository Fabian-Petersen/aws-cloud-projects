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
      each.value.enable_gsi ? flatten([
        for gsi in values(lookup(each.value, "gsis", {})) : [
          gsi.hash_key,
          try(gsi.range_key, null)
        ]
      ]) : []
    )))
    content {
      name = attribute.value
      type = "S"
    }
  }

  # dynamic "attribute" {
  #   for_each = distinct(compact(concat(
  #     [each.value.pk],
  #     [lookup(each.value, "sk", null)],
  #     each.value.enable_gsi ? [each.value.gsi.hash_key] : []
  #   )))
  #   content {
  #     name = attribute.value
  #     type = "S"
  #   }
  # }
  # dynamic "global_secondary_index" {
  #   for_each = each.value.enable_gsi ? [each.value.gsi] : []
  #   content {
  #     name            = global_secondary_index.value.name
  #     hash_key        = global_secondary_index.value.hash_key
  #     projection_type = global_secondary_index.value.projection
  #   }
  # }

  dynamic "global_secondary_index" {
    for_each = each.value.enable_gsi ? lookup(each.value, "gsis", {}) : {}
    content {
      name            = global_secondary_index.key
      hash_key        = global_secondary_index.value.hash_key
      range_key       = try(global_secondary_index.value.range_key, null)
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
