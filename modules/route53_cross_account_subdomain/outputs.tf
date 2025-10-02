output "subdomain_nameservers" {
  value = aws_route53_zone.subdomain.name_servers
  description = "Name servers for the 'uwc.fabian-portfolio.net' subdomain."
}

output "subdomain_zone_id" {
    value = aws_route53_zone.subdomain.zone_id
    description = "The zoneid for the subdomain, to be used to create the SSL certificates"
}