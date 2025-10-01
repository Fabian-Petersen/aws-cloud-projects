# $ Global variables
variable "project_name" {
  default     = "ec2_project"
  description = "The name of the project"
  type        = string
}
variable "region" {
  default     = "af-south-1"
  description = "aws region for the project"
  type        = string
}

variable "global_region" {
  default     = "us-east-1"
  description = "aws region for the SSL certificates"
  type        = string
}

variable "profile" {
  default     = "fabian-user2"
  description = "aws profile for the project"
  type        = string
}

variable "key_name" {
  default     = "ec2_project_sshkey"
  description = "ssh key for the ec2 instance"
  type        = string
}