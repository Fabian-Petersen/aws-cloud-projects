# $ ======================================= Main Account ========================================= #

provider "aws" {
  alias   = "main_account"
  profile = "fabian-user"
  region  = var.region
}

provider "aws" {
  alias   = "main_account_global"
  profile = "fabian-user"
  region  = var.global_region
}

# $ ===================================== Free Tier Account ====================================== #

provider "aws" {
  alias = "free_tier_account_global"
  # profile = "fabian-user2"
  profile = "default"
  region  = var.global_region

  # Manually create this role in the console to get role_arn
  # Add this role for DNS Validation of host domain
  # assume_role {
  #   role_arn = "arn:aws:iam::${var.profile_1_account_id}:role/delegation_trust_policy"
  # }
}

provider "aws" {
  alias = "free_tier_account"
  # profile = "fabian-user2"
  profile = "default"
  region  = var.region

  # Manually create this role in the console to get role_arn
  assume_role {
    role_arn = "arn:aws:iam::${var.profile_1_account_id}:role/delegation_trust_policy"
  }
}