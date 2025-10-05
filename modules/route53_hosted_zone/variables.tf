variable "primary_hosted_zone" {
  description = "parent domain in the root account"
  type        = string
  #   default     = "fabian-portfolio.net"
}

variable "secondary_hosted_zone" {
  description = "hosted zone in secondary account from primary account"
  type        = string
}

variable "subdomain_name" {
  #   default     = "www.uwc.fabian-portfolio.net"
  description = "subdomain for the website from parent domain"
  type        = string
}

variable "subdomain_nameservers" {
  #   default     = "www.uwc.fabian-portfolio.net"
  description = "Name servers for the 'uwc.fabian-portfolio.net' subdomain."
  type        = list(string)
}
