# Checks if Amazon CloudFront distributions are using a custom SSL certificate and are configured to use SNI to serve HTTPS requests. The rule is NON_COMPLIANT if a custom SSL certificate is associated but the SSL support method is a dedicated IP address.

# Identifier: CLOUDFRONT_SNI_ENABLED
# Resource Types: AWS::CloudFront::Distribution
# Trigger type: Configuration changes
# AWS Region: Only available in US East (N. Virginia) Region

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.0"

    }
  }
}

#$ [Step 1] : IAM Role for AWS Config to assume 
data "aws_iam_policy_document" "cloudfront_sni_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["config.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "cloudfront_rule" {
  name               = "cloudfront-awsconfig-role"
  assume_role_policy = data.aws_iam_policy_document.cloudfront_sni_role.json
}

# [] S3 Bucket Policy
data "aws_iam_policy_document" "s3-awsConfig-policy" {
  statement {
    effect  = "Allow"
    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.bucket_awsconfig.arn,
      "${aws_s3_bucket.bucket_awsconfig.arn}/*"
    ]
  }
}

resource "aws_iam_role_policy" "s3-awsConfig-policy" {
  name   = "awsconfig-example"
  role   = aws_iam_role.cloudfront_rule.id
  policy = data.aws_iam_policy_document.s3-awsConfig-policy.json
}

# (Optional) Attach a managed AWS policy so Config can record/write logs
resource "aws_iam_role_policy_attachment" "config_role_attach" {
  role       = aws_iam_role.cloudfront_rule.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWS_ConfigRole"
}


#$ [Step 2] : Configuration Recorder - AWS Config needs a recorder to capture resources
resource "aws_config_configuration_recorder" "enable_recorder" {
  name       = "default"
  role_arn   = aws_iam_role.cloudfront_rule.arn
  depends_on = [aws_config_delivery_channel.snapshot_logs]
}

#% [Optional] : Storing of the logs optional if continuous monitoring necessary where the state can change
resource "aws_s3_bucket" "bucket_awsconfig" {
  bucket = "awsconfig-${var.subdomain_name}"

  lifecycle {
    prevent_destroy = true
  }

  tags = {
    Name = "aws-config-logs"
  }
}

#$ [Step 3] Delivery Channel Required so AWS Config can deliver snapshots
resource "aws_config_delivery_channel" "snapshot_logs" {
  name           = "cloudfront_sni_compliance_logs"
  s3_bucket_name = aws_s3_bucket.bucket_awsconfig.bucket
}

#$ [Step 4] : Start the Recorder  
#% [INFO] : Without this, the recorder will exist but not run

resource "aws_config_configuration_recorder_status" "activate_recorder" {
  name       = aws_config_configuration_recorder.enable_recorder.name
  is_enabled = true
}

#$ [Step 5] Config Rule to check CloudFront SNI
resource "aws_config_config_rule" "cloudfront_rule" {
  name = "cloudfront_sni_rule"

  source {
    owner             = "AWS"
    source_identifier = "CLOUDFRONT_SNI_ENABLED"
  }

  depends_on = [
    aws_config_configuration_recorder_status.activate_recorder,
    aws_config_delivery_channel.snapshot_logs
  ]
}
