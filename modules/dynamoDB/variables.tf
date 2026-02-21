# variable "dynamoDB_table_names" {
#   type = list(string)
# }

# $ Changed the table variable to a map to scale if specific features are required per table
# $ Map variable makes the code easier for specific features.
variable "dynamodb_tables" {
  type = map(object({
    enable_gsi    = bool
    enable_stream = bool

    # Per-table primary key config
    pk = optional(string) # default "id" if not set
    sk = optional(string) # only set if you want a sort key

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

