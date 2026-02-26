variable "ssm_prefix" {
  type        = string
  description = "SSM path prefix."
}

variable "parameters" {
  description = "SSM parameters to create."
  type = map(object({
    value       = string
    type        = optional(string, "String")   # String | SecureString | StringList
    tier        = optional(string, "Standard") # Standard | Advanced
    description = optional(string, null)
  }))
}

variable "env" {}
variable "project_name" {}

