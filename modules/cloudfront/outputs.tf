output "distribution_id" {
  value = aws_cloudfront_distribution.distribution.id
}

output "cloudfront_domain_name" {
  value = aws_cloudfront_distribution.distribution.domain_name
}

# Use this output to get the cloudfront resource in json format. Run `terraform output -json distribution`
output "cloudfront_hosted_zone_id" {
  value = aws_cloudfront_distribution.distribution.hosted_zone_id
}

output "cloudfront_distribution_arn" {
  value = aws_cloudfront_distribution.distribution.arn
}