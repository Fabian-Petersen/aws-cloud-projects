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
  cognito_arn       = module.cognito.cognito_userpool_arn
  subdomain_name    = var.subdomain_name
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

  depends_on = [module.dynamodb_tables]
}

#$  // =================================== dynamoDB =================================== //
module "dynamodb_tables" {
  source = "../../modules/dynamoDB"
  # dynamoDB_table_names = var.dynamoDB_table_names # % List variable - "constrained to only name"
  env = var.env
  # table_gsi_map        = var.table_gsi_map
  dynamodb_tables = var.dynamodb_tables # % Map variable - added features can be passed in map
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
  users                  = var.users
  user_groups            = var.user_groups
}

#$ // ========================= pdf Lambda ======================== //
# This lambda is triggered by dynamodb streams to build the pdf jobcard once the status of the job changed. The created jobcard is stored in s3 /jobcards/*
data "aws_s3_bucket" "pdf_bucket" {
  bucket = "crud-nosql-app-images"
}
module "pdf_generator" {
  source               = "../../modules/pdf_generator"
  function_name        = var.function_name
  project_name         = var.project_name
  env                  = var.env
  packageType          = var.packageType
  image_uri            = var.image_uri
  dynamodb_table_names = ["crud-nosql-app-maintenance-request-table", "crud-nosql-app-maintenance-action-table"]
  s3_bucket_arn        = data.aws_s3_bucket.pdf_bucket.arn
  # runtime              = var.runtime
  dynamodb_stream_arn = module.dynamodb_tables.dynamodb_stream_arns["crud-nosql-app-maintenance-request"]
}

#$ // ========================= ecr Lambda ======================== //
module "ecr_pdf" {
  source          = "../../modules/ecr"
  env             = var.env
  repository_name = var.repository_name
  max_image_count = var.max_image_count
  scan_on_push    = var.scan_on_push
  project_name    = var.project_name
}

output "cognito_userpool_arn" {
  value = module.cognito.cognito_userpool_arn
}
