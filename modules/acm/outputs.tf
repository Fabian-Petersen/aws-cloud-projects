# output "domain_name" {
#   value = var.host_domain_name
# }

output "acm_certificate_arn" {
  value = aws_acm_certificate.subdomain_acm_certificate.arn
}


