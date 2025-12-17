terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.0"
    }
  }
}


#$ [Step 1] Look up the hosted zone in the main account
data "aws_route53_zone" "parent_zone" {
  name = var.primary_hosted_zone
}

#$ [Step 2] : Add Name Server records in Account A (parent zone) pointing to subdomain in Account B 
resource "aws_route53_record" "subdomain_ns" {
  zone_id = data.aws_route53_zone.parent_zone.zone_id
  name    = var.secondary_hosted_zone
  type    = "NS"
  ttl     = 300
  records = var.subdomain_nameservers

  lifecycle {
    prevent_destroy = true
  }
}
