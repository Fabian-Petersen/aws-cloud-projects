# terraform {
#   backend "s3" {
#     bucket       = "terraform-state-fabian-v2"
#     key          = "fabian-portfolio/terraform.tfstate"
#     region       = "af-south-1"
#     use_lockfile = true
#     encrypt      = true
#     profile      = "fabian-user"
#   }
# }

terraform {
  backend "s3" {
    bucket       = "terraform-state-fabian-v3"
    key          = "crud-nosql.app/terraform.tfstate"
    region       = "af-south-1"
    use_lockfile = true
    encrypt      = true
    profile      = "default"
  }
}
