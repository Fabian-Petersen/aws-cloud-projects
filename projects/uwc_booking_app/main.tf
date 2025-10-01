// dev environment - entry point
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.0"
    }
  }
}

# provider "aws" {
#   alias   = "free_tier_account_global"
#   profile = "fabian-user2"
#   region  = var.global_region

#   assume_role {
#     role_arn = "arn:aws:iam::${var.profile_2_account_id}:role/delegation_trust_policy"
#   }
# }
# $  // ================================= route 53 ================================ //

# Create the hosted zone in the child account via the module
module "subdomain" {
  source = "../modules/cross_account_subdomain"
  #   provider = aws.free_tier_account
  #   subdomain_name = "www.uwc.fabian-portfolio.net"
  subdomain_nameservers = data.aws_route53_zone.parent_zone.name_servers
}

# Look up the parent zone using the parent provider
data "aws_route53_zone" "parent_zone" {
  provider = aws.main_account
  name     = "fabian-portfolio.net"
}

# Delegate the NS record in the parent zone
resource "aws_route53_record" "subdomain_ns" {
  provider = aws.main_account
  zone_id  = data.aws_route53_zone.parent_zone.zone_id
  name     = "www.uwc.fabian-portfolio.net"
  type     = "NS"
  ttl      = 300
  # Get the Name Servers from the module's output
  records = module.subdomain.subdomain_nameservers
}

# $  // ====================================== acm ======================================= //

module "acm" {
  source = "../modules/acm"
  
  providers = {
    aws = aws.free_tier_account_global
  }

  hosted_zone             = "fabian-portfolio.net"
  subdomain_name          = "www.uwc.fabian-portfolio.net"
  redirect_subdomain_name = "uwc.fabian-portfolio.net"
}

# $  // =================================== cloudfront =================================== //

# module "cloudfront" {
#     source = "../modules/cloudfront"
#     profile = var.profile
#     project_name = var.project_name
#     env = var.env
#     acm_certificate_arn = var.acm_certificate_arn
# }

# $  // ===================== s3 buckets for website hosting ============================== //

module "s3_website_bucket" {
  source               = "../modules/s3_website_bucket"
  host_domain_name     = var.subdomain_name
  redirect_domain_name = var.redirect_subdomain_name
}

# $  // =================================== api gateway =================================== //


# $  // =================================== dynamoDB =================================== //

# $  // =================================== lambda functions =================================== //


