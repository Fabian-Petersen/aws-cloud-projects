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

variable "cloudfront_policies" {
  description = "Managed CloudFront policy IDs"
  type        = map(string)
}

variable "ordered_cache_items" {
  description = "List of ordered cache behaviors for CloudFront"
  type = list(object({
    path_pattern    = string
    allowed_methods = list(string)
  }))
}

variable "price_class" {}
variable "s3_origin_id" {}
