# $ This module takes in variables and create paramaters to be used in an application with the param arns as output.
resource "aws_ssm_parameter" "this" {
  for_each = var.parameters

  name        = "${each.value.prefix}/${each.key}"
  type        = each.value.type
  tier        = each.value.tier
  value       = each.value.value
  description = lookup(each.value, "description", "")

  overwrite = true

  tags = {
    Name        = "${var.project_name}-${each.key}"
    Environment = var.env
  }
}


# variable "parameters" {
#   type = map(object({
#     value       = string
#     description = optional(string)
#     prefix      = optional(string)  # allow custom SSM prefix
#   }))
# }

# locals {
#   default_prefix = "/crud-nosql"  # can be overridden per parameter
# }

# resource "aws_ssm_parameter" "parameters" {
#   for_each = var.parameters

#   name  = "${lookup(each.value, "prefix", local.default_prefix)}/${each.key}"
#   type  = "String"
#   value = each.value.value
#   description = lookup(each.value, "description", "")
# }
