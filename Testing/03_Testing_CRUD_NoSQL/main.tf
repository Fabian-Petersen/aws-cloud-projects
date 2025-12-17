// dev environment - entry point
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.0"
    }
  }
}

# $ // ================================= route 53 ================================ //

# module "route53_cross_account_subdomain" {
#   source                  = "../../modules/route53_cross_account_subdomain"
#   primary_hosted_zone     = var.primary_hosted_zone
#   secondary_hosted_zone   = var.secondary_hosted_zone
#   subdomain_name          = var.subdomain_name
#   redirect_subdomain_name = var.redirect_subdomain_name
# }

# # $ Access the parent zone to create the subdomain and to add the name servers
# module "route53_hosted_zone" {
#   source                = "../../modules/route53_hosted_zone"
#   primary_hosted_zone   = var.primary_hosted_zone
#   secondary_hosted_zone = var.secondary_hosted_zone
#   subdomain_name        = var.subdomain_name
#   subdomain_nameservers = module.route53_cross_account_subdomain.subdomain_nameservers

#   providers = {
#     aws = aws.main_account
#   }
# }

# $ // ====================================== acm ======================================= //

#$ [Step 1] Look up the hosted zone in the secondary account for ACM
data "aws_route53_zone" "hosted_zone" {
  name = var.hosted_zone
}

module "acm" {
  source = "../../modules/acm"

  hosted_zone             = var.secondary_hosted_zone
  subdomain_name          = var.subdomain_name
  redirect_subdomain_name = var.redirect_subdomain_name
  zone_id                 = data.aws_route53_zone.hosted_zone.zone_id

  providers = {
    aws = aws.free_tier_account_global
  }
}
# $ // =================================== cloudfront =================================== //

module "cloudfront" {
  source                  = "../../modules/cloudfront"
  subdomain_name          = var.subdomain_name
  redirect_subdomain_name = var.redirect_subdomain_name
  project_name            = var.project_name
  region                  = var.region
  acm_certificate_arn     = module.acm.acm_certificate_arn
  env                     = var.env
  secondary_hosted_zone   = var.secondary_hosted_zone
}

#$  // =================================== awsConfig =================================== //

# module "awsConfig" {
#   source         = "../../modules/awsConfig"
#   subdomain_name = var.subdomain_name

#   providers = {
#     aws = aws.free_tier_account_global
#   }
# }

#$ // ===================== s3 buckets for website hosting ============================== //

# module "s3_website_bucket" {
#   source                      = "../../modules/s3_website_bucket"
#   subdomain_name              = var.subdomain_name
#   redirect_subdomain_name     = var.redirect_subdomain_name
#   cloudfront_distribution_arn = module.cloudfront.cloudfront_distribution_arn
# }

#$  // =================================== api gateway =================================== //

module "apigateway" {
  source                = "../../modules/apigateway"
  api_routes            = var.api_routes
  lambda_arns           = module.lambda.lambda_invoke_arns
  lambda_function_names = module.lambda.lambda_function_names
}

#$ // =================================== lambda functions =================================== //

module "lambda" {
  source               = "../../modules/lambda/modules/dynamoDB"
  lambda_functions     = var.lambda_functions
  region               = var.region
  profile_2_account_id = var.profile_2_account_id
}

#$  // =================================== dynamoDB =================================== //
module "dynamodb_tables" {
  source               = "../../modules/dynamoDB"
  dynamoDB_table_names = var.dynamoDB_table_names
}

#$ // =================================== cognito =================================== //
# module "cognito" {
#   source                 = "../../modules/cognito"
#   env                    = var.env
#   project_name           = var.project_name
#   subdomain_name         = var.subdomain_name
#   region                 = var.region
#   acm_certificate_arn    = module.acm.acm_certificate_arn
#   test_user_email        = var.test_user_email
#   test_user_name         = var.test_user_name
#   test_user_username     = var.test_user_username
#   prevent_user_existence = var.prevent_user_existence
# }
