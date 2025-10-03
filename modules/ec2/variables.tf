variable "key_name" {
  description = "SSH Key pair name"
  type        = string
}

variable "security_group_ids" {
  description = "List of security group IDs"
  type        = list(string)
}

variable "ami_id" {
  description = "The AMI ID to use for the instance"
  type        = string
}

variable "instance_type" {
  default     = "t3.micro"
  description = "EC2 instance type"
  type        = string
}

variable "user_data" {
  description = "script file that runs on ec2 instance on bootup"
  type        = string
}

# variable "subnet_id" {
#   description = "Subnet ID"
#   type        = string
# }

variable "project_name" {
  description = "The name of the project"
  type        = string
}