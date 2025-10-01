# % ACM Certificate for the host and redirect domain
# % The certificate is created in the us-east-1 region, which is required for AWS CloudFront.
# % The certificate is created with DNS validation, and the validation records are created in Route 53.

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.0"

    }
  }
}


# $ [STEP 1] : Request the ACM certificate in the child (free tier account) account 

resource "aws_acm_certificate" "subdomain_acm_certificate" {
  domain_name               = var.subdomain_name
  validation_method         = "DNS"
  subject_alternative_names = [var.subdomain_name, var.redirect_subdomain_name]

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "${var.subdomain_name}_acm_certificate"
  }
}

# $ [Step 2] : Create validation records in the free tier account

data "aws_route53_zone" "subdomain_zone" {
  name         = var.subdomain_name
  private_zone = false
}

resource "aws_route53_record" "subdomain_cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.subdomain_acm_certificate.domain_validation_options : dvo.domain_name => dvo
  }

  zone_id = data.aws_route53_zone.subdomain_zone.zone_id
  name    = each.value.resource_record_name
  type    = each.value.resource_record_type
  records = [each.value.resource_record_value]
  ttl     = 300
}

# $ [Step 3] : Wait for validation to complete

resource "aws_acm_certificate_validation" "subdomain_cert_validation" {
  certificate_arn   = aws_acm_certificate.subdomain_acm_certificate.arn
  validation_record_fqdns = [for record in aws_route53_record.subdomain_cert_validation : record.fqdn]
}

# $ [Step 4] : Access the validated certificate's ARN
output "subdomain_certificate_arn" {
  value = aws_acm_certificate_validation.subdomain_cert_validation.certificate_arn
}