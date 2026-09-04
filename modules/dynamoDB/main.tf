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

  dynamic "global_secondary_index" {
    for_each = each.value.enable_gsi ? lookup(each.value, "gsis", {}) : {}
    content {
      name               = global_secondary_index.key
      projection_type    = global_secondary_index.value.projection_type
      non_key_attributes = try(global_secondary_index.value.non_key_attributes, null)

      dynamic "key_schema" {
        for_each = concat(
          [{
            attribute_name = global_secondary_index.value.hash_key
            key_type       = "HASH"
          }],
          try(global_secondary_index.value.range_key, null) != null ? [{
            attribute_name = global_secondary_index.value.range_key
            key_type       = "RANGE"
          }] : []
        )

        content {
          attribute_name = key_schema.value.attribute_name
          key_type       = key_schema.value.key_type
        }
      }
    }
  }

  stream_enabled   = each.value.enable_stream
  stream_view_type = each.value.enable_stream ? "NEW_AND_OLD_IMAGES" : null

  ttl {
    attribute_name = var.ttl_attribute
    enabled        = var.enable_ttl
  }

  tags = {
    Project = var.project_name
    Env     = var.env
    Name    = each.key
  }
}
