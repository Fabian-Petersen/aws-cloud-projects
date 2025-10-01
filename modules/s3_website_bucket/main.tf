# $ This module creates the S3 buckets for the project.
# % terraform import module.s3.aws_s3_bucket_policy.host_bucket_policy www.fabian-portfolio.net // command to import the S3 bucket policy

# $ Redirect Bucket
resource "aws_s3_bucket" "redirect_bucket" {
  bucket = var.host_domain_name

  tags = {
    Domain      = var.redirect_domain_name
    Environment = var.env
  }
}

resource "aws_s3_bucket_website_configuration" "redirect_bucket" {
  bucket = aws_s3_bucket.redirect_bucket.id

  redirect_all_requests_to {
    host_name = var.host_domain_name
    protocol  = "https"
  }
}

# $ Website Host Bucket
resource "aws_s3_bucket" "host_bucket" {
  bucket = var.host_domain_name

  tags = {
    Domain      = var.host_domain_name
    Environment = var.env
  }
}

resource "aws_s3_bucket_website_configuration" "host_bucket_config" {
  bucket = aws_s3_bucket.host_bucket.id

  index_document {
    suffix = "index.html"
  }
}

resource "aws_s3_bucket_cors_configuration" "host_bucket_cors" {
  bucket = aws_s3_bucket.host_bucket.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT", "POST", "GET", "DELETE", "HEAD"]
    allowed_origins = [var.host_domain_name]
    expose_headers  = []
    max_age_seconds = 3000
  }
}

resource "aws_s3_bucket_policy" "host_bucket_policy" {
  bucket = aws_s3_bucket.host_bucket.id
  policy = data.aws_iam_policy_document.host_bucket_policy.json
}

data "aws_iam_policy_document" "host_bucket_policy" {
  statement {
    actions = ["s3:GetObject"]
    resources = [
      "${aws_s3_bucket.host_bucket.arn}/*"
    ]

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }
  }
}
