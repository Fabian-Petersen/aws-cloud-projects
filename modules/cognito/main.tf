#$ // ============================== cognito_app_integration ================================ //
module "cognito" {
  source                 = "./modules/cognito_app_integration"
  env                    = var.env
  project_name           = var.project_name
  subdomain_name         = var.subdomain_name
  region                 = var.region
  acm_certificate_arn    = var.acm_certificate_arn
  test_user_email        = var.test_user_email
  test_user_name         = var.test_user_name
  test_user_username     = var.test_user_username
  prevent_user_existence = var.prevent_user_existence
}