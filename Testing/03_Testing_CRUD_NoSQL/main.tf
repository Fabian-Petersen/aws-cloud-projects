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
  api_id                  = module.apigateway.api_id
  cloudfront_policies     = var.cloudfront_policies
  ordered_cache_items     = var.ordered_cache_items
  price_class             = var.price_class
  s3_origin_id            = var.s3_origin_id

  depends_on = [module.acm]
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
  source            = "../../modules/apigateway"
  api_parent_routes = var.api_parent_routes
  api_child_routes  = var.api_child_routes
  lambda_arns       = module.lambda.lambda_invoke_arns
  lambda_functions  = var.lambda_functions
  api_name          = var.api_name
  env               = var.env
  project_name      = var.project_name
  # authorizer_id      = var.env == "dev" ? null : aws_apigatewayv2_authorizer.cognito.id
}

#$ // =========================== API Method lambda functions ========================== //

module "lambda" {
  source               = "../../modules/lambda/modules/dynamoDB"
  lambda_functions     = var.lambda_functions
  region               = var.region
  profile_2_account_id = var.profile_2_account_id
  extra_policies       = var.extra_policies
}

#$ // =========================== lambda triggered by s3 ============================== //

module "s3_event_lambda" {
  source      = "../../modules/lambda/modules/s3"
  file_name   = var.file_name
  bucket_name = var.bucket_name
  table_names = var.table_names
  lambda_name = var.lambda_name
  handler     = var.handler
}

# output "lambda_arns" {
#   value = module.lambda.lambda_invoke_arns
# }

#$  // =================================== dynamoDB =================================== //
module "dynamodb_tables" {
  source               = "../../modules/dynamoDB"
  dynamoDB_table_names = var.dynamoDB_table_names
  env                  = var.env
}

#$ // =================================== cognito =================================== //
module "cognito" {
  source                 = "../../modules/cognito"
  env                    = var.env
  project_name           = var.project_name
  subdomain_name         = var.subdomain_name
  region                 = var.region
  acm_certificate_arn    = module.acm.acm_certificate_arn
  test_user_email        = var.test_user_email
  test_user_name         = var.test_user_name
  test_user_username     = var.test_user_username
  prevent_user_existence = var.prevent_user_existence
}

#$ // ========================= File Upload to S3 & DynamoDB ======================== //


#$ // ========================= pdf Lambda ======================== //
module "pdf_generator" {
  source              = "../../modules/pdf_generator"
  project_name        = "maintenance-app"
  environment         = "prod"
  dynamodb_table_name = var.dynamodb_table_name
  lambda_zip_path     = var.lambda_zip_path
  s3_bucket           = var.bucket_name
  runtime             = var.runtime
}

#$ // ========================= ecr Lambda ======================== //
module "ecr_pdf" {
  source = "../../modules/ecr"

  repository_name = var.repository_name
  max_image_count = var.max_image_count
  scan_on_push    = var.scan_on_push

}
