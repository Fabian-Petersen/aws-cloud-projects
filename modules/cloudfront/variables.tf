variable "subdomain_name" {
  description = "subdomain for the website from parent domain"
  type        = string
}

variable "redirect_subdomain_name" {
  description = "redirect to for the website"
  type        = string
}

variable "acm_certificate_arn" {
  type = string
}

variable "project_name" {
  type = string
}

variable "region" {
  type = string
}

variable "env" {
  type = string
}

variable "secondary_hosted_zone" {
}

variable "api_id" {
  type = string
}
