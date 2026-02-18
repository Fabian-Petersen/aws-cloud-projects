# $ This module create the cloudfront distribution for the website with the redirect alias.
# $ The module use the gloabl region us-east-1, which is required for AWS CloudFront.
# $ The origin is an S3 bucket, and the distribution is configured with multiple cache behaviors.
# % terraform import module.cloudfront.aws_cloudfront_distribution.distribution E20QZ4G1Y7PO33
# bucket url "http://uwc.app.fabian-portfolio.net.s3.af-south-1.amazonaws.com"
# origin regional endpoint without OAC fabian-portfolio.net: www.fabian-portfolio.net.s3-website.af-south-1.amazonaws.com
# Create invalidation "aws cloudfront create-invalidation --distribution-id <Distribution-ID> --paths "/*" "

#% [INFO] : Local variables that can be used inside module
locals {
  my_domain  = var.subdomain_name
  bucket_url = "${var.subdomain_name}.s3.${var.region}.amazonaws.com"
}

#$ [Step 1] : Get the SSL Certificate from Certifcate Manager
data "aws_acm_certificate" "my_domain" {
  region   = "us-east-1"
  domain   = var.subdomain_name
  statuses = ["ISSUED"]
}


#$ [Step 2] : Create CloudFront Origin Access Control for s3 bucket access
resource "aws_cloudfront_origin_access_control" "oac" {
  name                              = "${var.subdomain_name}-oac"
  description                       = "Origin Access Control for S3 origin"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always" # recommended: always sign requests
  signing_protocol                  = "sigv4"
}

#$ [Step 3] : Create the Cloudfront distribution
resource "aws_cloudfront_distribution" "distribution" {
  price_class         = var.price_class // Price"PriceClass_200"
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "CloudFront distribution for ${var.subdomain_name}"
  default_root_object = "index.html"
  aliases             = ["${var.subdomain_name}", "${var.redirect_subdomain_name}"]

  #% [INFO] : S3 Bucket Origin for the website
  origin {
    domain_name              = local.bucket_url
    origin_access_control_id = aws_cloudfront_origin_access_control.oac.id
    origin_id                = var.s3_origin_id

    #% [Note] : custom_origin_config is for non s3 buckets e.g. EC2, ALB, etc 
    s3_origin_config {
      origin_access_identity = "" # leave empty when using OAC
    }
  }

  #% [INFO] : Access the root of the website "/" This will create Default(*) behavior
  default_cache_behavior {
    target_origin_id       = var.s3_origin_id
    allowed_methods        = ["HEAD", "GET", "OPTIONS"]
    cached_methods         = ["HEAD", "GET"]
    viewer_protocol_policy = "redirect-to-https"
    compress               = true
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0

    #% Managed-CachingDisabled: Caching Disabled,all requests forwarded to origin
    cache_policy_id = var.cloudfront_policies.caching_optimized

    #% Set to 'Managed-CORS-S3Origin'
    origin_request_policy_id = var.cloudfront_policies.cors_s3_origin
  }

  #% [INFO] : Manage the routes e.g. through the API /bookings, /contacts etc.
  #% [INFO] : Each cache bahvior have it's own config settings
  #% [INFO] : The  precedence is order listed from 0 and is similar to Behaviors in the console
  # $ API Gateway Origin for the API backend
  origin {
    connection_attempts      = 3
    connection_timeout       = 10
    domain_name              = "${var.api_id}.execute-api.af-south-1.amazonaws.com"
    origin_id                = "${var.api_id}.execute-api.af-south-1.amazonaws.com"
    origin_access_control_id = null
    origin_path              = "/dev"

    custom_origin_config {
      http_port                = 80
      https_port               = 443
      origin_keepalive_timeout = 5
      origin_protocol_policy   = "https-only"
      origin_read_timeout      = 30
      origin_ssl_protocols = [
        "TLSv1.2",
      ]
    }
  }


  dynamic "ordered_cache_behavior" {
    for_each = var.ordered_cache_items
    content {
      target_origin_id       = "${var.api_id}.execute-api.af-south-1.amazonaws.com"
      path_pattern           = ordered_cache_behavior.value.path_pattern
      allowed_methods        = ordered_cache_behavior.value.allowed_methods
      cached_methods         = ["GET", "HEAD"]
      compress               = true
      default_ttl            = 0
      max_ttl                = 0
      min_ttl                = 0
      smooth_streaming       = false
      trusted_key_groups     = []
      trusted_signers        = []
      viewer_protocol_policy = "redirect-to-https"

      #% Managed policies
      cache_policy_id            = var.cloudfront_policies.caching_disabled
      origin_request_policy_id   = var.cloudfront_policies.allViewerExceptHostHeader
      response_headers_policy_id = var.cloudfront_policies.CORSwithPreflightSecurityHeadersPolicy
    }
  }

  restrictions {
    geo_restriction {
      locations        = []
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn            = var.acm_certificate_arn
    cloudfront_default_certificate = false
    minimum_protocol_version       = "TLSv1.2_2021"
    ssl_support_method             = "sni-only"
  }

  tags = {
    Environment = var.env
    Project     = var.project_name
  }
}

#$ [Step 4] : Create Route53 records for the CloudFront distribution aliases
data "aws_route53_zone" "hosted_zone" {
  name = var.secondary_hosted_zone
}

resource "aws_route53_record" "cloudfront" {
  for_each = aws_cloudfront_distribution.distribution.aliases
  zone_id  = data.aws_route53_zone.hosted_zone.zone_id
  name     = each.value
  type     = "A"

  lifecycle {
    create_before_destroy = true
  }

  alias {
    name                   = aws_cloudfront_distribution.distribution.domain_name
    zone_id                = aws_cloudfront_distribution.distribution.hosted_zone_id
    evaluate_target_health = false
  }
}

#! ======================================= END ==============================================
