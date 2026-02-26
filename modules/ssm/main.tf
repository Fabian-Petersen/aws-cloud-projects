# $ This module takes in variables and create paramaters to be used in an application with the param arns as output.

resource "aws_ssm_parameter" "this" {
  for_each = var.parameters

  name        = "${var.ssm_prefix}/${each.key}"
  type        = each.value.type
  tier        = each.value.tier
  value       = each.value.value
  description = each.value.description

  overwrite = true

  tags = {
    Name        = "${var.project_name}-${each.key}"
    Environment = var.env
  }
}
