
# $ Get the hosted zone to create the subdomain of the main account
data "aws_route53_zone" "hosted_zone" {
  provider     = aws.main_account
  name         = "${var.hosted_zone}."
  private_zone = false
}

# $ Root account delegating the subdomain
resource "aws_route53_record" "subdomain_delegation" {
  provider = aws.main_account
  zone_id  = aws_route53_zone.hosted_zone.zone_id
  name     = "uwc.fabian-portfolio.net"
  type     = "NS"
  ttl      = 300
  records  = var.subdomain_nameservers # This will be the NS records from the child account
}


resource "aws_route53_zone" "subdomain_zone" {
  provider = aws.free_tier_account
  name     = var.host_domain_name
}


# $ Create Route53 record for the subdomain in main account
resource "aws_route53_record" "subdomain" {
  provider = aws.main_account
  zone_id  = data.aws_route53_zone.hosted_zone.id
  name     = var.host_domain_name
  type     = "A"

  alias {
    name                   = var.host_domain_name # S3 website endpoint
    zone_id                = var.host_domain_name # S3 website hosted zone ID
    evaluate_target_health = false
  }
}