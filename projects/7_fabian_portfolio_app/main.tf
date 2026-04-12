#$ // ========================= SSM Params ======================== //
# % This module create paramters for the SES module
module "ssm" {
  source       = "../../modules/ssm"
  env          = var.env
  project_name = var.project_name
  parameters   = var.parameters
}
