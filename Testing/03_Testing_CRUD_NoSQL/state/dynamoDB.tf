resource "aws_dynamodb_table" "dynamodb_table" {
  arn                         = "arn:aws:dynamodb:af-south-1:157489943321:table/crud-nosql-app-images-table"
  billing_mode                = "PAY_PER_REQUEST"
  deletion_protection_enabled = false
  hash_key                    = "id"
  id                          = "crud-nosql-app-images-table"
  name                        = "crud-nosql-app-images-table"
  read_capacity               = 0
  region                      = "af-south-1"
  stream_arn                  = null
  stream_enabled              = false
  stream_label                = null
  stream_view_type            = null
  table_class                 = "STANDARD"
  tags = {
    "Env"  = "dev"
    "Name" = "crud-nosql-app-images"
  }
  tags_all = {
    "Env"  = "dev"
    "Name" = "crud-nosql-app-images"
  }
  write_capacity = 0

  attribute {
    name = "id"
    type = "S"
  }

  point_in_time_recovery {
    enabled                 = false
    recovery_period_in_days = 0
  }

  ttl {
    attribute_name = null
    enabled        = false
  }
}
