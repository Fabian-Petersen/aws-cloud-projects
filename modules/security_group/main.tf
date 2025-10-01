# Security Group
resource "aws_security_group" "ec2-security-group" {
  name        = "${var.project_name}-sg"
  description = "Security group for EC2 instancee."
  # vpc_id      = "vpc-xxxxxxxx" # Replace with your VPC ID

  # Inbound rules
  ingress {
    description = "Allow SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["102.217.43.179/32"] # $ Restrict this in production
  }

  ingress {
    description = "Allow HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound rules
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-ec2-sg"
  }
}