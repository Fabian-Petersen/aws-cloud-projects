output "rule_arns" {
  value = {
    for k, rule in aws_cloudwatch_event_rule.rules :
    k => rule.arn
  }
}
