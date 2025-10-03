# $ Name of the bucket the same as domain hence the domain used as naming variables
variable "root_hosted_zone" {
  # default     = "fabian-portfolio.net"
  description = "hosted zone in the main account in the main account"
  type        = string
}

# variable "project_hosted_zone" {
#   # default     = "app.fabian-portfolio.net"
#   description = "hosted zone in free account with root zone in main account"
#   type        = string
# }

variable "subdomain_name" {
  # default     = "uwc.app.fabian-portfolio.net"
  description = "subdomain for the website from parent domain"
  type        = string
}

variable "redirect_subdomain_name" {
  # default     = "www.uwc.app.fabian-portfolio.net"
  description = "redirect to for the website"
  type        = string
}

variable "env" {
  default     = "env"
  description = "development environment"
  type        = string
}
variable "cloudfront_distribution_arn" {
  type = string
}
