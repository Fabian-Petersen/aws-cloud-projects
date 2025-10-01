output "key_name" {
  description = "value of the test spot instance key pair"
  value       = aws_key_pair.SSH_key.key_name
}