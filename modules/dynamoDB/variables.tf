# variable "dynamoDB_table_names" {
#   type = list(string)
# }

# $ Changed the table variable to a map to scale if specific features are required per table
# $ Map variable makes the code easier for specific features.
variable "dynamodb_tables" {
  type = map(object({
    enable_gsi    = bool
    enable_stream = bool

    gsi = optional(object({
      name       = string
      hash_key   = string
      projection = string
    }))
  }))
}
variable "env" {
  type = string
}

# Optional GSI map: key = table_name, value = GSI config
# variable "table_gsi_map" {
#   type = map(object({
#     name       = string
#     hash_key   = string
#     projection = string
#   }))
#   default = {}
# }

