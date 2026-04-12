terraform {
  backend "s3" {
    bucket       = "fabian-portfolio-terraform-state"
    key          = "fabian-portfolio/terraform.tfstate"
    region       = "af-south-1"
    use_lockfile = true
    encrypt      = true
    profile      = "fabian-user"
  }
}
