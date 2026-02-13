variable "dynamoDB_table_names" {
  type = list(string)
}

variable "env" {
  type = string
}

# Optional GSI map: key = table_name, value = GSI config
variable "table_gsi_map" {
  type = map(object({
    name      = string
    hash_key  = string
    projection = string
  }))
  default = {}
}

variable "gsi_hash_key" {
  type = string
}

variable "gsi_name" {
  type = string
}
