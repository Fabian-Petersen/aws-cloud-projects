# $ This module create the cloudfront distribution for the website with the redirect alias.
# $ The module use the gloabl region us-east-1, which is required for AWS CloudFront.
# $ The origin is an S3 bucket, and the distribution is configured with multiple cache behaviors.
# % terraform import module.cloudfront.aws_cloudfront_distribution.distribution E20QZ4G1Y7PO33
# bucket url "http://uwc.app.fabian-portfolio.net.s3.af-south-1.amazonaws.com"
# origin regional endpoint without OAC fabian-portfolio.net: www.fabian-portfolio.net.s3-website.af-south-1.amazonaws.com
# origin api-gateway: sigrcfirp1.execute-api.af-south-1.amazonaws.com

# locals {
# s3_origin_id = "s3-origin-${var.host_domain_name_id}"

# ordered_cache_items = [
#   {
#     path_pattern    = "/bookings"
#     allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]

#   },
# {
#   path_pattern    = "/booking"
#   allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]

# },
# {
#   path_pattern    = "/"
#   allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]

# },
# {
#   path_pattern    = "/fabian_cv_latest.pdf"
#   allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
# }
# ]
# }

#% [INFO] : Local variables that can be used inside module
locals {
  s3_origin_id = "s3-origin"
  my_domain    = var.subdomain_name
  bucket_url   = "${var.subdomain_name}.s3.${var.region}.amazonaws.com"
}

#$ [Step 1] : Get the SSL Certificate from Certifcate Manager
data "aws_acm_certificate" "my_domain" {
  region   = "us-east-1"
  domain   = var.subdomain_name
  statuses = ["ISSUED"]
}

#$ [Step 2] : Create CloudFront Origin Access Control for s3 bucket access
resource "aws_cloudfront_origin_access_control" "oac" {
  name                              = "${var.subdomain_name}-origin access"
  description                       = "Origin Access Contol Policy for S3 origin"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always" # recommended: always sign requests
  signing_protocol                  = "sigv4"
}

#$ [Step 3] : Create the Cloudfront distribution
resource "aws_cloudfront_distribution" "distribution" {
  price_class         = "PriceClass_200"
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "CloudFront distribution for ${var.subdomain_name}"
  default_root_object = "index.html"
  aliases             = ["${var.subdomain_name}", "${var.redirect_subdomain_name}"]

  #% [INFO] : S3 Bucket Origin for the website
  origin {
    domain_name              = local.bucket_url
    origin_access_control_id = aws_cloudfront_origin_access_control.oac.id
    origin_id                = local.s3_origin_id

    #% [Note] : custom_origin_config is for non s3 buckets e.g. EC2, ALB, etc 
    s3_origin_config {
      origin_access_identity = "" # leave empty when using OAC
    }
    # custom_origin_config {
    #   http_port                = 80
    #   https_port               = 443
    #   origin_keepalive_timeout = 5
    #   origin_read_timeout      = 30
    #   origin_protocol_policy   = "http-only"
    #   origin_ssl_protocols     = ["SSLv3", "TLSv1", "TLSv1.1", "TLSv1.2", ]
    # }
  }

  default_cache_behavior {
    target_origin_id       = local.s3_origin_id
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    viewer_protocol_policy = "redirect-to-https"
    compress               = true
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0

    forwarded_values {
      query_string = false

      cookies {
        forward = "none"
      }
    }
  }

  #% [INFO] : Access the root of the website "/"
  #% [INFO] : Manage the routes e.g. through the API /bookings, /contacts etc.
  #% [INFO] : Each cache bahvior have it's own config settings
  #% [INFO] : The  precedence is order listed from 0 and is similar to Behaviors in the console
  ordered_cache_behavior {
    target_origin_id = local.s3_origin_id
    path_pattern     = "/*"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]

    forwarded_values {
      query_string = false
      headers      = ["Origin"]

      cookies {
        forward = "none"
      }
    }

    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
    compress               = true
    viewer_protocol_policy = "redirect-to-https"
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
    prevent_destroy = true
  }

  alias {
    name                   = aws_cloudfront_distribution.distribution.domain_name
    zone_id                = aws_cloudfront_distribution.distribution.hosted_zone_id
    evaluate_target_health = false
  }
}

#! ======================================= END ==============================================
# resource "aws_cloudfront_distribution" "distribution" {
#   price_class     = "PriceClass_200"
#   enabled         = true
#   is_ipv6_enabled = true
#   comment         = "CloudFront distribution for ${var.subdomain_name}"
#   aliases         = [var.subdomain_name, var.redirect_subdomain_name]

# $ S3 Bucket Origin for the website
# origin {
#   domain_name         = "${var.subdomain_name}.s3.${var.region}.amazonaws.com"
#   origin_id           = "s3-origin"
#   origin_access_control_id = aws_cloudfront_origin_access_control.oac.id
#   connection_attempts = 3
#   connection_timeout  = 10

#   custom_origin_config {
#     http_port                = 80
#     https_port               = 443
#     origin_keepalive_timeout = 5
#     origin_read_timeout      = 30
#     origin_protocol_policy   = "http-only"
#     origin_ssl_protocols     = ["SSLv3", "TLSv1", "TLSv1.1", "TLSv1.2", ]
#   }
# }

# $ API Gateway Origin for the API backend
# origin {
#   connection_attempts      = 3
#   connection_timeout       = 10
#   domain_name              = "${var.api_id}.execute-api.af-south-1.amazonaws.com"
#   origin_id                = "${var.api_id}.execute-api.af-south-1.amazonaws.com"
#   origin_access_control_id = null
#   origin_path              = "/dev"

#   custom_origin_config {
#     http_port                = 80
#     https_port               = 443
#     origin_keepalive_timeout = 5
#     origin_protocol_policy   = "https-only"
#     origin_read_timeout      = 30
#     origin_ssl_protocols = [
#       "TLSv1.2",
#     ]
#   }
# }

# default_cache_behavior {
#   allowed_methods          = ["GET", "HEAD"]
#   cached_methods           = ["GET", "HEAD"]
#   target_origin_id         = "s3-origin"
#   viewer_protocol_policy   = "redirect-to-https"
#   compress                 = true
#   default_ttl              = 0
#   max_ttl                  = 0
#   min_ttl                  = 0
#   smooth_streaming         = false
# }

# ordered_cache_behavior {
#   target_origin_id         = "sigrcfirp1.execute-api.af-south-1.amazonaws.com"
#   path_pattern             = local.ordered_cache_items[0].path_pattern
#   allowed_methods          = local.ordered_cache_items[0].allowed_methods
#   cache_policy_id          = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
#   cached_methods           = ["GET", "HEAD"]
#   compress                 = true
#   default_ttl              = 0
#   max_ttl                  = 0
#   min_ttl                  = 0
#   origin_request_policy_id = "59781a5b-3903-41f3-afcb-af62929ccde1"
#   smooth_streaming         = false
#   trusted_key_groups       = []
#   trusted_signers          = []
#   viewer_protocol_policy   = "redirect-to-https"

#   grpc_config {
#     enabled = false
#   }
# }

# ordered_cache_behavior {
#   target_origin_id         = "sigrcfirp1.execute-api.af-south-1.amazonaws.com"
#   path_pattern             = local.ordered_cache_items[1].path_pattern
#   allowed_methods          = local.ordered_cache_items[1].allowed_methods
#   cache_policy_id          = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
#   cached_methods           = ["GET", "HEAD"]
#   compress                 = true
#   default_ttl              = 0
#   max_ttl                  = 0
#   min_ttl                  = 0
#   origin_request_policy_id = "88a5eaf4-2fd4-4709-b370-b4c650ea3fcf"
#   smooth_streaming         = false
#   trusted_key_groups       = []
#   trusted_signers          = []
#   viewer_protocol_policy   = "redirect-to-https"

#   grpc_config {
#     enabled = false
#   }
# }

# ordered_cache_behavior {
#   target_origin_id         = "sigrcfirp1.execute-api.af-south-1.amazonaws.com"
#   allowed_methods          = local.ordered_cache_items[2].allowed_methods
#   path_pattern             = local.ordered_cache_items[2].path_pattern
#   cache_policy_id          = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
#   cached_methods           = ["GET", "HEAD"]
#   compress                 = true
#   default_ttl              = 0
#   max_ttl                  = 0
#   min_ttl                  = 0
#   origin_request_policy_id = "88a5eaf4-2fd4-4709-b370-b4c650ea3fcf"
#   smooth_streaming         = false
#   trusted_key_groups       = []
#   trusted_signers          = []
#   viewer_protocol_policy   = "redirect-to-https"

#   grpc_config {
#     enabled = false
#   }
# }

# ordered_cache_behavior {
#   allowed_methods          = local.ordered_cache_items[3].allowed_methods
#   cache_policy_id          = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
#   cached_methods           = ["GET", "HEAD"]
#   compress                 = true
#   default_ttl              = 0
#   max_ttl                  = 0
#   min_ttl                  = 0
#   origin_request_policy_id = "88a5eaf4-2fd4-4709-b370-b4c650ea3fcf"
#   path_pattern             = local.ordered_cache_items[3].path_pattern
#   smooth_streaming         = false
#   target_origin_id         = "sigrcfirp1.execute-api.af-south-1.amazonaws.com"
#   trusted_key_groups       = []
#   trusted_signers          = []
#   viewer_protocol_policy   = "redirect-to-https"

#   grpc_config {
#     enabled = false
#   }
# }

# ordered_cache_behavior {
#   allowed_methods          = ["GET", "HEAD"]
#   cache_policy_id          = "658327ea-f89d-4fab-a63d-7e88639e58f6"
#   cached_methods           = ["GET", "HEAD"]
#   compress                 = true
#   default_ttl              = 0
#   max_ttl                  = 0
#   min_ttl                  = 0
#   origin_request_policy_id = "88a5eaf4-2fd4-4709-b370-b4c650ea3fcf"
#   path_pattern             = "/project/*"
#   smooth_streaming         = false
#   target_origin_id         = "sigrcfirp1.execute-api.af-south-1.amazonaws.com"
#   trusted_key_groups       = []
#   trusted_signers          = []
#   viewer_protocol_policy   = "redirect-to-https"

#   grpc_config {
#     enabled = false
#   }
# }

#   restrictions {
#     geo_restriction {
#       locations        = []
#       restriction_type = "none"
#     }
#   }

#   viewer_certificate {
#     acm_certificate_arn            = var.acm_certificate_arn
#     cloudfront_default_certificate = false
#     minimum_protocol_version       = "TLSv1.2_2021"
#     ssl_support_method             = "sni-only"
#   }

#   tags = {
#     Environment = var.env
#     Project     = var.project_name
#   }
# }

