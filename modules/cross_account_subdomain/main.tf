# $ This m,odules creates a subdomain from a parent domain in a different account (e.g. main account -> free tier account)

# main.tf in module
resource "aws_route53_zone" "subdomain_zone" {
  name = var.host_domain_name
}

output "subdomain_name_servers" {
  value = aws_route53_zone.subdomain_zone.name_servers
}