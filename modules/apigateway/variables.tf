variable "root_hosted_zone" {
#   default     = "fabian-portfolio.net"
  description = "hosted zone in the main account in the main account"
  type        = string
}

variable "project_hosted_zone" {
#   default     = "app.fabian-portfolio.net"
  description = "hosted zone in free account with root zone in main account"
  type        = string
}

variable "subdomain_name" {
#   default     = "uwc.app.fabian-portfolio.net"
  description = "subdomain for the website from parent domain"
  type        = string
}

variable "redirect_subdomain_name" {
#   default     = "www.uwc.app.fabian-portfolio.net"
  description = "redirect to for the website"
  type        = string
}

variable "project_name" {
#   default     = "uwc-booking-app"
  description = "The name of the project"
  type        = string
}