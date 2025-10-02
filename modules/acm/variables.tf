variable "hosted_zone" {
  description = "parent domain in the root account"
  type        = string
  # default     = "fabian-portfolio.net"
}

variable "subdomain_name" {
  # default     = "www.uwc.fabian-portfolio.net"
  description = "subdomain for the website from parent domain"
  type        = string
}

variable "redirect_subdomain_name" {
  # default     = "uwc.fabian-portfolio.net"
  description = "redirect to for the website"
  type        = string
}

variable "profile_2_account_id" {
  default     = "157489943321"
  description = "free tier account id"
  type        = string
}

variable "zone_id" {
  description = "zone_id of the subdomain"
  type = string
}