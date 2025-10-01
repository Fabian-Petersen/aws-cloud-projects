// dev environment - entry point
terraform {
  required_version = ">= 1.5.0"
}

# $ configure aws provider
provider "aws" {
  region  = var.region
  profile = var.profile
}

# $ Create Security Groups 
module "security_group" {
  source       = "../modules/security_group"
  project_name = var.project_name
}

# $ Create EC2 key pair
module "ec2_key_pair" {
  source       = "../modules/ec2_key_pair"
  project_name = var.project_name
  key_name     = "uwc-booking-app_sshkey"
}


# $ Create EC2 Instance
data "aws_ami" "ubuntu" {
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
  owners = ["099720109477"] # Canonical
}

variable "instance_type" {
  default     = "t3.micro"
  description = "ec2 instance"
  type        = string
}

module "ec2" {
  source             = "../modules/ec2"
  ami_id             = data.aws_ami.ubuntu.id
  instance_type      = "t3.micro"
  project_name       = var.project_name
  key_name           = var.key_name
  user_data          = "./ec2_script.sh"
  security_group_ids = [module.security_group.security-group-id]
}

output "private_ip" {
  value = module.ec2.private_ip
}

output "public_ip" {
  value = module.ec2.public_ip
}