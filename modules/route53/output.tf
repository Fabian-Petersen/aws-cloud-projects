output "subdomain_nameservers" {
  value       = aws_route53_zone.subdomain_zone.name_servers
  description = "Name servers for the 'staging.example.com' subdomain."
}