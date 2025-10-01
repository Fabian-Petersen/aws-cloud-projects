output "host_bucket_id" {
  value = aws_s3_bucket.host_bucket.id
}

output "host_bucket_name" {
  value = aws_s3_bucket.host_bucket.bucket
}

output "redirect_bucket_id" {
  value = aws_s3_bucket.redirect_bucket.id
}
output "redirect_bucket_name" {
  value = aws_s3_bucket.redirect_bucket.bucket
}

output "host_bucket_url" {
  value = aws_s3_bucket.host_bucket.bucket_domain_name
}