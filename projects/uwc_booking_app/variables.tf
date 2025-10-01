# $ Global variables
variable "project_name" {
  default     = "uwc-booking-app"
  description = "The name of the project"
  type        = string
}

variable "region" {
  default     = "af-south-1"
  description = "aws region for the project"
  type        = string
}

variable "env" {
  default     = "env"
  description = "development environment"
  type        = string
}

variable "global_region" {
  default     = "us-east-1"
  description = "aws region for the SSL certificates"
  type        = string
}

variable "profile_1" {
  default     = "fabian-user"
  description = "aws profile for the main account"
  type        = string
}

variable "profile_2" {
  default     = "fabian-user2"
  description = "free tier profile"
  type        = string
}

variable "profile_2_account_id" {
  default     = "157489943321"
  description = "free tier account id"
  type        = string
}

variable "key_name" {
  default     = "uwc-booking-app_sshkey"
  description = "ssh key for the ec2 instance"
  type        = string
}

variable "hosted_zone" {
  description = "parent domain in the root account"
  type        = string
  default     = "fabian-portfolio.net"
}

variable "subdomain_name" {
  default     = "www.uwc.fabian-portfolio.net"
  description = "subdomain for the website from parent domain"
  type        = string
}

variable "redirect_subdomain_name" {
  default     = "uwc.fabian-portfolio.net"
  description = "redirect to for the website"
  type        = string
}