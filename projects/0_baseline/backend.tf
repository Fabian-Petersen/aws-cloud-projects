# terraform {
#   backend "s3" {
#     bucket       = "terraform-state-fabian-v2"
#     key          = "state_dev/terraform.tfstate"
#     region       = "af-south-1"
#     use_lockfile = true
#     encrypt      = true
#     profile      = "fabian-user"
#     dynamodb_table = "terraform-locks-fabian-v2"
#   }
# }

terraform {
  backend "s3" {
    bucket         = "terraform-state-fabian-v3"
    key            = "uwc-booking-app/terraform.tfstate"
    region         = "af-south-1"
    use_lockfile   = true
    encrypt        = true
    profile        = "fabian-user2"
    dynamodb_table = "terraform-locks-fabian-v3"
  }
}