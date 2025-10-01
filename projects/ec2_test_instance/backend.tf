terraform {
  backend "s3" {
    bucket       = "terraform-state-fabian-v3"
    key          = "fabian-portfolio/terraform.tfstate"
    region       = "af-south-1"
    use_lockfile = true
    encrypt      = true
    profile      = "fabian-user2"
  }
}

