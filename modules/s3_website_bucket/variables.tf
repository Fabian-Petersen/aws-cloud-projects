# $ Name of the bucket the same as domain hence the domain used as naming variables
variable "redirect_domain_name" {
  description = "The redirect domain"
  type        = string
}

variable "host_domain_name" {
  description = "domain the website point to"
  type        = string
}

variable "env" {
  default     = "env"
  description = "development environment"
  type        = string
}