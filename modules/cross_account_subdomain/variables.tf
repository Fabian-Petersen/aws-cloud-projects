variable "hosted_zone" {
  default     = "fabian-portfolio.net"
  description = "parent domain in the root account"
  type        = string
}

variable "host_domain_name" {
  default     = "www.uwc.fabian-portfolio.net"
  description = "subdomain for the website from parent domain"
  type        = string
}

variable "redirect_domain_name" {
  default     = "uwc.fabian-portfolio.net"
  description = "redirect to for the website"
  type        = string
}

variable "subdomain_nameservers" {
  description = "Name servers of the delegated subdomain in the child account."
  type        = list(string)
}
