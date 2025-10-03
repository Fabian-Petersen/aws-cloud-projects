# $ This module creates the S3 buckets for the project.
# % terraform import module.s3.aws_s3_bucket_policy.host_bucket_policy www.fabian-portfolio.net // command to import the S3 bucket policy

#$ [STEP 1] : Create the website host bucket
resource "aws_s3_bucket" "host_bucket" {
  bucket = var.subdomain_name

  #% [INFO] : Once create don't remove unless website removed
  lifecycle {
    prevent_destroy = true
  }

  tags = {
    Domain      = var.subdomain_name
    Environment = var.env
  }
}

#$ [Step 2] : Create the redirect bucket 
resource "aws_s3_bucket" "redirect_bucket" {
  bucket = var.redirect_subdomain_name

  #% [INFO] : Once create don't remove unless website removed
  lifecycle {
    prevent_destroy = true
  }
  tags = {
    Domain      = var.redirect_subdomain_name
    Environment = var.env
  }
}

#$ [Step 3] : Configure the host bucket  
resource "aws_s3_bucket_website_configuration" "host_bucket_config" {
  bucket = aws_s3_bucket.host_bucket.id

  index_document {
    suffix = "index.html"
  }
}

#$ [Step 4] : Configure the redirect bucket  
resource "aws_s3_bucket_website_configuration" "redirect_bucket" {
  bucket = aws_s3_bucket.redirect_bucket.id

  redirect_all_requests_to {
    host_name = var.subdomain_name
    protocol  = "https"
  }
}

#$ [Step 5] : Configure the CORS settings for the host bucket  
resource "aws_s3_bucket_cors_configuration" "host_bucket_cors" {
  bucket = aws_s3_bucket.host_bucket.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT", "POST", "GET", "DELETE", "HEAD"]
    allowed_origins = [var.subdomain_name]
    expose_headers  = []
    max_age_seconds = 3000
  }
}

#$ [Step 6] : Create the origin access policy to allow cloudfront to access content in host bucket  
data "aws_iam_policy_document" "origin_bucket_policy" {
  statement {
    sid    = "AllowCloudFrontServicePrincipalReadWrite"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.host_bucket.arn}/*"]

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [var.cloudfront_distribution_arn]
    }
  }
}

#$ [Step 7] : Apply the policy to the host bucket  
resource "aws_s3_bucket_policy" "host_bucket_policy" {
  bucket = aws_s3_bucket.host_bucket.bucket
  policy = data.aws_iam_policy_document.origin_bucket_policy.json
}