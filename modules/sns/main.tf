locals {
  sns_publish_lambdas = {
    for k, v in aws_lambda_function.this :
    k => v.arn
    if try(var.lambda_functions_custom[k].publish_sns, false)
  }
}

resource "aws_sns_topic" "this" {
  for_each = var.topics

  name = each.value.name
}

resource "aws_sns_topic_subscription" "email" {
  for_each = {
    for k, v in var.topics :
    k => v.email_subscriptions
    if length(v.email_subscriptions) > 0
  }

  topic_arn = aws_sns_topic.this[each.key].arn
  protocol  = "email"
  endpoint  = each.value[0]
}

resource "aws_sns_topic_subscription" "sms" {
  for_each = {
    for k, v in var.topics :
    k => v.sms_subscriptions
    if length(v.sms_subscriptions) > 0
  }

  topic_arn = aws_sns_topic.this[each.key].arn
  protocol  = "sms"
  endpoint  = each.value[0]
}

resource "aws_sns_platform_application" "push" {
  for_each            = var.topics
  count               = each.value.enable_push ? 1 : 0
  name                = "${each.value.name}-push"
  platform            = "GCM" # or APNS, APNS_SANDBOX, etc.
  platform_credential = var.fcm_key
}

resource "aws_sns_topic_policy" "this" {
  for_each = var.topics

  arn = aws_sns_topic.this[each.key].arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowLambdaPublish"
        Effect = "Allow"

        Principal = {
          AWS = "*"
        }

        Action = "sns:Publish"

        Resource = aws_sns_topic.this[each.key].arn

        Condition = {
          ArnEquals = {
            "aws:SourceArn" = var.allowed_lambda_arns
          }
        }
      }
    ]
  })
}
