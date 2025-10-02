// dev environment - entry point
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.0"
    }
  }
}

# $  // ================================= route 53 ================================ //

module "route53_cross_account_subdomain" {
  source         = "../../modules/route53_cross_account_subdomain"
  subdomain_name = "uwc.app.fabian-portfolio.net"
}

# $ Access the parent zone to create the subdomain and to add the name servers
module "route53_hosted_zone" {
  source                = "../../modules/route53_hosted_zone"
  hosted_zone           = "fabian-portfolio.net"
  subdomain_name        = "app.fabian-portfolio.net"
  subdomain_nameservers = module.route53_cross_account_subdomain.subdomain_nameservers

  providers = {
    aws = aws.main_account
  }
}

# $  // ====================================== acm ======================================= //

module "acm" {
  source = "../../modules/acm"

  providers = {
    aws = aws.free_tier_account_global
  }

  hosted_zone             = "fabian-portfolio.net"
  subdomain_name          = "uwc.app.fabian-portfolio.net"
  redirect_subdomain_name = "www.uwc.app.fabian-portfolio.net"
  zone_id                 = module.route53_cross_account_subdomain.subdomain_zone_id
}

# $  // =================================== cloudfront =================================== //

module "cloudfront" {
  source                  = "../../modules/cloudfront"
  project_name            = "uwc_booking_app"
  region                  = "af-south-1"
  acm_certificate_arn     = module.acm.acm_certificate_arn
  subdomain_name          = "uwc.app.fabian-portfolio.net"
  redirect_subdomain_name = "www.uwc.app.fabian-portfolio.net"
  # host_bucket_id          = module.s3_website_bucket.host_bucket_id
  env = "dev"
}

module "awsConfig" {
  source          = "../../modules/awsConfig"
  subdomain_name  = "uwc.app.fabian-portfolio.net"

  providers = {
    aws = aws.free_tier_account_global
  }
}

# $  // ===================== s3 buckets for website hosting ============================== //

module "s3_website_bucket" {
  source                      = "../../modules/s3_website_bucket"
  root_hosted_zone            = "fabian-portfolio.net"
  subdomain_name              = "uwc.app.fabian-portfolio.net"
  redirect_subdomain_name     = "www.uwc.app.fabian-portfolio.net"
  cloudfront_distribution_arn = module.cloudfront.cloudfront_distribution_arn
}

# $  // =================================== api gateway =================================== //
# module "apigateway" {
#   source                      = "../../modules/apigateway"
#   # root_hosted_zone            = "fabian-portfolio.net"
#   # subdomain_name              = "uwc.app.fabian-portfolio.net"
#   # redirect_subdomain_name     = "www.uwc.app.fabian-portfolio.net"
#   # cloudfront_distribution_arn = module.cloudfront.cloudfront_distribution_arn
# }

# $  // =================================== dynamoDB =================================== //

# $  // =================================== lambda functions =================================== //


