# $ Create a EC2 instance

resource "aws_instance" "ec2_instance" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  vpc_security_group_ids = var.security_group_ids
  key_name               = var.key_name

# $ This file will run to install docker once the ec2 is created
  user_data = file(var.user_data)
  tags = {
    Name = "${var.project_name}-ec2-instance"
  }
}