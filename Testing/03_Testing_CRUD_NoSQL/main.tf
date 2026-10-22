// dev environment - entry point
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.0"
    }

    # Add time to delay the dkim token to propagate for 10s
    time = {
      source  = "hashicorp/time"
      version = "~> 0.9"
    }
  }
}


# In your terraform required_providers block:

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
  # source = "../../modules/acm"
  source = "git::https://github.com/Fabian-Petersen/terraform-modules.git//acm?ref=v1.0.2"

  hosted_zone             = var.secondary_hosted_zone
  subdomain_name          = var.subdomain_name
  redirect_subdomain_name = var.redirect_subdomain_name
  zone_id                 = data.aws_route53_zone.hosted_zone.zone_id
  tags                    = var.tags

  providers = {
    aws = aws.free_tier_account_global
  }
}
# $ // =================================== cloudfront =================================== //

module "cloudfront" {
  # source                  = "../../modules/cloudfront"
  source                  = "git::https://github.com/Fabian-Petersen/terraform-modules.git//cloudfront?ref=v1.0.2"
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
  tags                    = var.tags

  # depends_on = [module.acm]
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
  # source                  = "../../modules/apigateway"
  source                  = "git::https://github.com/Fabian-Petersen/terraform-modules.git//apigateway?ref=v1.0.2"
  api_parent_routes       = var.api_parent_routes
  api_child_routes        = var.api_child_routes
  lambda_arns             = merge(module.lambda.lambda_invoke_arns, module.cognito_lambda.custom_lambda_invoke_arns)
  lambda_functions        = var.lambda_functions
  lambda_functions_custom = var.lambda_functions_custom
  api_name                = var.api_name
  env                     = var.env
  project_name            = var.project_name
  cognito_arn             = module.cognito.cognito_userpool_arn
  subdomain_name          = var.subdomain_name
}

#$ // =========================== IAM Policy ========================== //
# $ Create additional IAM policies per lambda (Optional)

module "iam_lambda" {
  # source          = "../../modules/iam"
  source            = "git::https://github.com/Fabian-Petersen/terraform-modules.git//iam?ref=v1.0.2"
  lambda_functions  = var.lambda_functions
  lambda_role_names = module.lambda.lambda_role_names
  tags              = var.tags
}

#$ // =========================== API Method lambda functions ========================== //

module "lambda" {
  # source = "../../modules/lambda/modules/dynamoDB"
  source               = "git::https://github.com/Fabian-Petersen/terraform-modules.git//lambda/modules/dynamoDB?ref=v1.0.2"
  lambda_functions     = var.lambda_functions
  region               = var.region
  profile_2_account_id = var.profile_2_account_id
  extra_policies       = var.extra_policies
  env                  = var.env
  project_name         = var.project_name
  tags                 = var.tags
}

#$ // =========================== lambda triggered by s3 ============================== //

module "s3_event_lambda" {
  # source       = "../../modules/lambda/modules/s3"
  source       = "git::https://github.com/Fabian-Petersen/terraform-modules.git//lambda/modules/s3?ref=v1.0.2"
  file_name    = var.file_name
  bucket_name  = var.bucket_name
  table_names  = var.table_names
  lambda_name  = var.lambda_name
  handler      = var.handler
  env          = var.env
  project_name = var.project_name
  tags         = var.tags

  # Removed the dependency on the dynamodb_tables during migration to remote module source. Ensure that the dynamodb_tables module is applied before this module if necessary.
  # depends_on = [module.dynamodb_tables]
}

#$ // ============ Technicians Lambda with Cognito (custom lambdas) =================== //
module "cognito_lambda" {
  # source                  = "../../modules/lambda/modules/lambda"
  source                  = "git::https://github.com/Fabian-Petersen/terraform-modules.git//lambda/modules/lambda?ref=v1.0.2"
  lambda_functions_custom = var.lambda_functions_custom
  env                     = var.env
  project_name            = var.project_name
  tags                    = var.tags
}

#$  // =================================== dynamoDB =================================== //
module "dynamodb_tables" {
  # source = "../../modules/dynamoDB"
  source = "git::https://github.com/Fabian-Petersen/terraform-modules.git//dynamoDB?ref=v1.0.2"
  # dynamoDB_table_names = var.dynamoDB_table_names # % List variable - "constrained to only name"
  env             = var.env
  project_name    = var.project_name
  dynamodb_tables = var.dynamodb_tables # % Map variable - added features can be passed in map
  enable_ttl      = var.enable_ttl
  ttl_attribute   = var.ttl_attribute
  tags            = var.tags
}

#$ // =================================== cognito =================================== //
module "cognito" {
  # source                 = "../../modules/cognito"
  source                 = "git::https://github.com/Fabian-Petersen/terraform-modules.git//cognito?ref=v1.0.2"
  env                    = var.env
  project_name           = var.project_name
  subdomain_name         = var.subdomain_name
  region                 = var.region
  acm_certificate_arn    = module.acm.acm_certificate_arn
  test_user_email        = var.test_user_email
  test_user_name         = var.test_user_name
  test_user_username     = var.test_user_username
  prevent_user_existence = var.prevent_user_existence
  user_groups            = var.user_groups
  users                  = var.users
  tags                   = var.tags

  # lambda_triggers        = module.cognito_lambda.custom_lambda_arns
}

#$ // ========================= pdf Lambda ======================== //
# % This lambda is triggered by dynamodb streams to build the pdf jobcard once the status of the job changed. The created jobcard is stored in s3 /jobcards/*
data "aws_s3_bucket" "pdf_bucket" {
  bucket = "crud-nosql-app-images"
}
module "pdf_generator" {
  # source               = "../../modules/pdf_generator"
  source               = "git::https://github.com/Fabian-Petersen/terraform-modules.git//pdf_generator?ref=v1.0.2"
  function_name        = var.function_name
  project_name         = var.project_name
  env                  = var.env
  packageType          = var.packageType
  image_uri            = var.image_uri
  dynamodb_table_names = ["crud-nosql-app-maintenance-request-table", "crud-nosql-app-maintenance-action-table"]
  s3_bucket_arn        = data.aws_s3_bucket.pdf_bucket.arn
  # runtime              = var.runtime
  dynamodb_stream_arn = module.dynamodb_tables.dynamodb_stream_arns["crud-nosql-app-maintenance-request"]
  tags                = var.tags
}

#$ // ========================= ecr Lambda ======================== //
module "ecr_pdf" {
  # source          = "../../modules/ecr"
  source          = "git::https://github.com/Fabian-Petersen/terraform-modules.git//ecr?ref=v1.0.2"
  env             = var.env
  repository_name = var.repository_name
  max_image_count = var.max_image_count
  scan_on_push    = var.scan_on_push
  project_name    = var.project_name
  tags            = var.tags
}

#$ // ========================= SSM Params ======================== //
# % This module create paramters for the SES module
module "ssm" {
  # source       = "../../modules/ssm"
  source       = "git::https://github.com/Fabian-Petersen/terraform-modules.git//ssm?ref=v1.0.2"
  env          = var.env
  project_name = var.project_name
  parameters   = var.parameters
  tags         = var.tags
}

#$ // ========================= SES Lambda ======================== //
# This module create the lambda, SSM Parameters and SES to send an email once a user create a maintenance request and email the request details to the admin for approval.
# module "ses_notify" {
#   source = "../../modules/ses"
# ssm_param_arns = module.ssm.ssm_param_arns
# lambda_function_name = var.lambda_function_name
# dynamodb_stream_arn = module.dynamodb_tables.dynamodb_stream_arns["crud-nosql-app-maintenance-request"]
# }

module "ses" {
  # source              = "../../modules/ses"
  source              = "git::https://github.com/Fabian-Petersen/terraform-modules.git//ses?ref=v1.0.2"
  env                 = var.env
  region              = var.region
  project_name        = var.project_name
  from_email          = var.from_email
  dynamodb_stream_arn = module.dynamodb_tables.dynamodb_stream_arns["crud-nosql-app-maintenance-request"]
  # % ================ ssm parameters =================
  ssm_param_names = module.ssm.ssm_param_names
  ssm_param_arns  = module.ssm.ssm_param_arns # map(string) convert to list(string) inside module

  # % ================ lambda function ================
  ses_function_name  = var.ses_function_name
  ses_filename       = var.ses_filename
  ses_lambda_handler = var.ses_lambda_handler
  runtime            = var.runtime

  #% ================= hosted zone ===================== 
  zone_id        = data.aws_route53_zone.hosted_zone.zone_id
  subdomain_name = var.subdomain_name
  tags           = var.tags
}

#$ // ========================= Event Bridge ======================== //

# output "debug_stream_tables" {
#   value = module.eventbridge.debug_stream_tables
# }

module "eventbridge" {
  # source = "../../modules/eventBridge"
  source = "git::https://github.com/Fabian-Petersen/terraform-modules.git//eventBridge?ref=v1.0.2"
  env    = var.env

  project_name          = var.project_name
  region                = var.region
  dynamodb_tables       = var.dynamodb_tables
  event_subscriptions   = var.event_subscriptions
  dynamodb_stream_arns  = module.dynamodb_tables.dynamodb_stream_arns
  profile_2_account_id  = var.profile_2_account_id
  scheduler_group_name  = var.scheduler_group_name
  scheduler_target_arns = merge(module.lambda.scheduler_targets_arns, module.cognito_lambda.scheduler_targets_arns)
  tags                  = var.tags

  resource_permissions = flatten([
    for rule_name, rule in var.event_subscriptions : [
      for target in rule.targets : {
        service   = target.target_type
        principal = "events.amazonaws.com"

        target_name = target.name
        source_arn  = module.eventbridge.rule_arns[rule_name]
        target_arn = (
          target.target_type == "lambda" ? module.cognito_lambda.custom_lambda_arns[target.name] :
          target.target_type == "sqs" ? module.sqs.queue_arns[target.name] :
          null
        )
      }
    ]
  ])
}

#$ // ========================== SQS ============================== //

module "sqs" {
  # source              = "../../modules/sqs"
  source              = "git::https://github.com/Fabian-Petersen/terraform-modules.git//sqs?ref=v1.0.2"
  queues              = var.queues
  sqs_lambda_triggers = var.sqs_lambda_triggers
  project_name        = var.project_name
  env                 = var.env
  tags                = var.tags
}


/* -------------------------------------------------------------------------- */
/*                                   OUTPUTS                                  */
/* -------------------------------------------------------------------------- */

# output "eventbridge_permission_arn_map" {
#   value = module.eventbridge.permission_arn_map
# }

# output "eventbridge_target_map" {
#   value = module.eventbridge.target_map
# }

# output "sqs_queues_arns" {
#   value = module.sqs.queue_arns
# }
