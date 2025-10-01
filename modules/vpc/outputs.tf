output "vpc_id" {
  description = "Private IP address of the EC2 instance"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "List of public subnet IDs in the VPC"
  value       = aws_subnet.public_subnet_az_a[*].id
}

output "private_subnet_ids" {
  description = "List of private subnet IDs in the VPC"
  value       = aws_subnet.private_subnet_az_a[*].id
}

output "public_sg" {
  description = "Security group ID for the VPC"
  value       = aws_security_group.public_sg.id
}