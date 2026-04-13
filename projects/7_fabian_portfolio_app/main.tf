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

#$ // ========================= SSM Params ======================== //
# % This module create paramters for the SES module
module "ssm" {
  source       = "../../modules/ssm"
  env          = var.env
  project_name = var.project_name
  parameters   = var.parameters
}
