# $ Zip the existing Lambda functions from /lambdas/<function_directory>
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.root}/lambdas/jobs-notify-admin/jobs-notify-admin.py"
  output_path = "${path.root}/lambdas/jobs-notify-admin/${replace("jobs-notify-admin.py", ".py", ".zip")}"
}

# $ [Step 1] : Create an IAM role for the Lambda function to execute operations on dynamoDB
resource "aws_iam_role" "lambda_exec_role" {
  name = "${var.ses_function_name}_exec_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# $ [Step 2] : Create the policy : Get SSM Parameters, GetItem from DynamoDB & send email templete to SES

data "aws_iam_policy_document" "lambda_policy" {
  statement {
    effect    = "Allow"
    actions   = ["ssm:GetParameter", "ssm:GetParameters"]
    resources = values(var.ssm_param_arns)
  }

  statement {
    effect    = "Allow"
    actions   = ["ses:SendEmail", "ses:SendRawEmail"]
    resources = ["*"]
  }
  statement {
    effect = "Allow"
    actions = ["dynamodb:DescribeStream", "dynamodb:GetRecords", "dynamodb:GetShardIterator", "dynamodb:ListStreams"
    ]
    resources = [var.dynamodb_stream_arn]
  }

  statement {
    effect    = "Allow"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["*"]
  }
}

# Convert the policy to json
resource "aws_iam_policy" "lambda_ses_notify" {
  name   = "${var.ses_function_name}-policy"
  policy = data.aws_iam_policy_document.lambda_policy.json
}


resource "aws_iam_role_policy_attachment" "attach" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_ses_notify.arn
}

# $ [Step 3] : Create the lambda function
resource "aws_lambda_function" "lambda_function" {
  function_name    = var.ses_function_name
  role             = aws_iam_role.lambda_exec_role.arn
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  filename         = data.archive_file.lambda_zip.output_path # match the filename and the hash source to avoid weird behavior
  handler          = var.ses_lambda_handler
  runtime          = var.runtime

  environment {
    variables = {
      SSM_PARAMS_JSON = jsonencode(var.ssm_param_names)
      SES_FROM_EMAIL  = var.from_email
    }
  }
}

#$ [Step 4] : Invoke the lambda with dynamoDB streams
resource "aws_lambda_event_source_mapping" "dynamoDB_to_lambda" {
  event_source_arn  = var.dynamodb_stream_arn
  function_name     = aws_lambda_function.lambda_function.arn
  starting_position = "LATEST"
  batch_size        = 5
  enabled           = true
}

# $ =========================== Email Verification & Records ============================== //

# resource "aws_ses_email_identity" "from" {
#   email = var.from_email
# }

# [INFO] defines domain
resource "aws_ses_domain_identity" "domain" {
  domain = var.subdomain_name
}

# [INFO] Generate tokens
resource "aws_ses_domain_dkim" "dkim" {
  domain = aws_ses_domain_identity.domain.domain
}
# $ Allow the tokens to propagate to prevent possible failure of dkim
resource "time_sleep" "dkim_propagation" {
  depends_on      = [aws_ses_domain_dkim.dkim]
  create_duration = "10s"
}

# % DKIM records (3 CNAMEs) - SES provides these tokens after identity creation
resource "aws_route53_record" "ses_dkim" {
  count = 3

  zone_id = var.zone_id
  name    = "${aws_ses_domain_dkim.dkim.dkim_tokens[count.index]}._domainkey.${var.subdomain_name}"
  type    = "CNAME"
  ttl     = 300

  records = [
    "${aws_ses_domain_dkim.dkim.dkim_tokens[count.index]}.dkim.amazonses.com."
  ]

  # KEY FIX: explicit depends_on prevents race condition
  depends_on = [time_sleep.dkim_propagation]

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "ses_spf" {
  zone_id = var.zone_id
  name    = var.subdomain_name
  type    = "TXT"
  ttl     = 300

  records = ["v=spf1 include:amazonses.com -all"]
}
resource "aws_route53_record" "dmarc" {
  zone_id = var.zone_id
  name    = "_dmarc.${var.subdomain_name}"
  type    = "TXT"
  ttl     = 300

  # Start with p=none while testing, then move to quarantine/reject later
  records = ["v=DMARC1; p=none; rua=mailto:dmarc@${var.subdomain_name}; fo=1"]
}

# $ Verify everything works to prevent a silent fail later
resource "aws_ses_domain_identity_verification" "dkim_verification" {
  domain     = aws_ses_domain_identity.domain.id
  depends_on = [aws_route53_record.ses_dkim]

  timeouts {
    create = "5m"
  }
}

# $ SES Domain Verification
resource "aws_route53_record" "ses_domain_verification" {
  zone_id = var.zone_id
  name    = "_amazonses.${var.subdomain_name}"
  type    = "TXT"
  ttl     = 300
  records = [aws_ses_domain_identity.domain.verification_token]

  depends_on = [aws_ses_domain_identity.domain]
}

#$ Console commands to re-create the expired tokens
# Force Terraform to re-create the DKIM resource and re-issue tokens
# - terraform taint aws_ses_domain_dkim.dkim

# Then re-apply — this recreates the tokens and rewrites the CNAMEs
# - terraform apply


# When SES sends you another expiry warning, just change reverify_trigger to "v2" and run terraform apply — it re-issues fresh tokens without destroying and recreating everything.
resource "null_resource" "ses_dkim_reverify" {
  triggers = {
    # Change this value to force re-verification on next apply
    reverify_trigger = "v1"
  }

  provisioner "local-exec" {
    command = "aws ses verify-domain-dkim --domain ${var.subdomain_name} --region ${var.region}"
  }

  depends_on = [aws_route53_record.ses_dkim]
}
