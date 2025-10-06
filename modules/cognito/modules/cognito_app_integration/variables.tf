variable "project_name" {
  description = "The name of the project"
  type        = string
}

variable "subdomain_name" {
  description = "subdomain for the website from parent domain"
  type        = string
}

variable "acm_certificate_arn" {
  description = "SSL domain certificate for the domain used by cognito"
  type        = string
}

variable "region" {
  description = "aws region for the project"
  type        = string
}

# Add ENABLED in production environments
variable "prevent_user_existence" {
  description = "Confirm if user exist if api hit fail, not ideal in production"
  type        = string
}

variable "test_user_username" {
  description = "test username"
  type        = string
}

variable "test_user_name" {
  description = "name of the user to be used as test"
  type        = string
}

variable "test_user_email" {
  description = "test user email"
  type        = string
}

variable "env" {
  type = string
}