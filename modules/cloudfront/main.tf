# $ This module create the cloudfront distribution for the website with the redirect alias.
# $ The module use the gloabl region us-east-1, which is required for AWS CloudFront.
# $ The origin is an S3 bucket, and the distribution is configured with multiple cache behaviors.
# % terraform import module.cloudfront.aws_cloudfront_distribution.distribution E20QZ4G1Y7PO33

provider "aws" {
  region = var.global_region
  profile = var.profile
}

locals {
  s3_origin_id = "s3-origin-${var.host_domain_name_id}"

  ordered_cache_items = [
    {
      path_pattern    = "/bookings"
      allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]

    },
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
  ]
}

resource "aws_cloudfront_distribution" "distribution" {
  price_class     = "PriceClass_200"
  enabled         = true
  is_ipv6_enabled = true
  comment         = "CloudFront distribution for ${var.host_domain_name}"
  aliases         = [var.host_domain_name, var.redirect_domain_name]

  # $ S3 Bucket Origin for the website
  origin {
    connection_attempts = 3
    connection_timeout  = 10
    domain_name         = "${var.host_domain_name}.s3-website.af-south-1.amazonaws.com"
    origin_id           = "${var.host_domain_name_id}.s3-website.af-south-1.amazonaws.com"

    custom_origin_config {
      http_port                = 80
      https_port               = 443
      origin_keepalive_timeout = 5
      origin_read_timeout      = 30
      origin_protocol_policy   = "http-only"
      origin_ssl_protocols     = ["SSLv3", "TLSv1", "TLSv1.1", "TLSv1.2", ]
    }
  }

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

  default_cache_behavior {
    allowed_methods          = ["GET", "HEAD"]
    cached_methods           = ["GET", "HEAD"]
    target_origin_id         = "${var.host_domain_name}.s3-website.af-south-1.amazonaws.com"
    viewer_protocol_policy   = "redirect-to-https"
    compress                 = true
    cache_policy_id          = "658327ea-f89d-4fab-a63d-7e88639e58f6"
    origin_request_policy_id = "88a5eaf4-2fd4-4709-b370-b4c650ea3fcf"
    default_ttl              = 0
    max_ttl                  = 0
    min_ttl                  = 0
    smooth_streaming         = false
  }

  ordered_cache_behavior {
    allowed_methods          = local.ordered_cache_items[0].allowed_methods
    cache_policy_id          = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
    cached_methods           = ["GET", "HEAD"]
    compress                 = true
    default_ttl              = 0
    max_ttl                  = 0
    min_ttl                  = 0
    origin_request_policy_id = "59781a5b-3903-41f3-afcb-af62929ccde1"
    path_pattern             = local.ordered_cache_items[0].path_pattern
    smooth_streaming         = false
    target_origin_id         = "sigrcfirp1.execute-api.af-south-1.amazonaws.com"
    trusted_key_groups       = []
    trusted_signers          = []
    viewer_protocol_policy   = "redirect-to-https"

    grpc_config {
      enabled = false
    }
  }

  # ordered_cache_behavior {
  #   allowed_methods          = local.ordered_cache_items[1].allowed_methods
  #   cache_policy_id          = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
  #   cached_methods           = ["GET", "HEAD"]
  #   compress                 = true
  #   default_ttl              = 0
  #   max_ttl                  = 0
  #   min_ttl                  = 0
  #   origin_request_policy_id = "88a5eaf4-2fd4-4709-b370-b4c650ea3fcf"
  #   path_pattern             = local.ordered_cache_items[1].path_pattern
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
  #   allowed_methods          = local.ordered_cache_items[2].allowed_methods
  #   cache_policy_id          = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
  #   cached_methods           = ["GET", "HEAD"]
  #   compress                 = true
  #   default_ttl              = 0
  #   max_ttl                  = 0
  #   min_ttl                  = 0
  #   origin_request_policy_id = "88a5eaf4-2fd4-4709-b370-b4c650ea3fcf"
  #   path_pattern             = local.ordered_cache_items[2].path_pattern
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

