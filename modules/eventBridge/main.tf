locals {
  # Return map of tables where enable_stream is true
  stream_tables = {
    for name, table in var.dynamodb_tables :
    name => table
    if table.enable_stream
  }

  # Build name => ARN lookup from resource_permissions
  permission_arn_map = {
    for perm in var.resource_permissions :
    perm.target_name => perm.target_arn
  }

  #   EventBridge creates one target resource per destination. If a rule has multiple targets, we need to create a unique resource for each target. We can use the rule name + target name as the key.
  flattened_targets = flatten([
    for rule_name, rule in var.event_subscriptions : [
      for target in rule.targets : {
        rule_name   = rule_name
        target_name = target.name
        target_arn  = lookup(local.permission_arn_map, target.name, null) # Look up the ARN for this target from the resource_permissions variable
        target_type = target.target_type
      }
    ]
  ])
  # Convert to map:
  target_map = {
    for target in local.flattened_targets :
    "${target.rule_name}-${target.target_name}" => target
  }

  resource_permissions_map = {
    for idx, perm in var.resource_permissions :
    "${perm.service}-${idx}" => perm
  }
}

# $ Step 1 : EventBridge Pipe (Stream to Bus)
# IAM Role for EventBridge Pipe
resource "aws_iam_role" "pipe_role" {
  for_each = local.stream_tables
  name     = "${var.project_name}-${each.key}-pipe-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "pipes.amazonaws.com" }
    }]
  })

  tags = {
    Project     = var.project_name
    Module      = "EventBridge"
    Environment = var.env
  }
}

# $ Step 2: IAM Policies for Pipe (Read Stream, Write to EventBridge)
resource "aws_iam_role_policy" "pipe_policy" {
  for_each = local.stream_tables
  name     = "${var.project_name}-${each.key}-pipe-execution-policy"
  role     = aws_iam_role.pipe_role[each.key].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetRecords",
          "dynamodb:GetShardIterator",
          "dynamodb:DescribeStream",
          "dynamodb:ListStreams"
        ]
        Resource = [var.dynamodb_stream_arns[each.key]] //dynamodb_streams_arns[each.key].stream_arn
      },
      {
        Effect   = "Allow"
        Action   = ["events:PutEvents"]
        Resource = aws_cloudwatch_event_bus.custom_event_bus.arn
      }
    ]
  })
}

# $ Step 3: Create the EventBridge Pipe per table with stream enabled, using native filtering to only pass INSERT events
resource "aws_pipes_pipe" "dynamoDB_to_eventbridge" {
  for_each = local.stream_tables

  name     = "${var.project_name}-${each.key}-pipe"
  role_arn = aws_iam_role.pipe_role[each.key].arn

  source = var.dynamodb_stream_arns[each.key]
  target = aws_cloudwatch_event_bus.custom_event_bus.arn

  # Native filtering: Only pass INSERT (Create Item) events to the bus
  source_parameters {
    dynamodb_stream_parameters {
      starting_position = "LATEST"
      batch_size        = 1
    }

    dynamic "filter_criteria" {
      for_each = each.value.stream_filter != null ? [1] : []
      content {
        filter {
          pattern = jsonencode({ eventName = each.value.stream_filter })
        }
      }
    }
  }
  target_parameters {
    eventbridge_event_bus_parameters {
      source      = each.value.event_source
      detail_type = each.value.event_detail_type
    }
  }

  tags = {
    Project     = var.project_name
    Module      = "EventBridge Pipe"
    Environment = var.env
  }
}

# $ Step 4: Create Custom EventBridge Event Bus
resource "aws_cloudwatch_event_bus" "custom_event_bus" {
  name = "${var.project_name}-event-bus"

  tags = {
    Project     = var.project_name
    Module      = "EventBridge Bus"
    Environment = var.env
  }
}

# $ Step 5: EventBridge Rule to Lambda (Bus to Lambda or target resource)
resource "aws_cloudwatch_event_rule" "rules" {
  for_each = var.event_subscriptions

  name           = "${var.project_name}-${each.key}-rule"
  event_bus_name = aws_cloudwatch_event_bus.custom_event_bus.name

  event_pattern = jsonencode({
    source      = [each.value.source]
    detail-type = [each.value.detail_type]
  })
}

# Link Rule to resource Target
resource "aws_cloudwatch_event_target" "targets" {
  for_each = local.target_map

  rule           = aws_cloudwatch_event_rule.rules[each.value.rule_name].name
  event_bus_name = aws_cloudwatch_event_bus.custom_event_bus.name

  target_id = each.value.target_name
  arn       = each.value.target_arn
}

# Permission for EventBridge to invoke Lambda
resource "aws_lambda_permission" "allow_eventbridge" {
  for_each = {
    for k, p in local.resource_permissions_map :
    k => p
    if p.service == "lambda"
  }

  statement_id  = "AllowEB-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = each.value.target_arn
  principal     = each.value.principal
  source_arn    = each.value.source_arn

  depends_on = [aws_cloudwatch_event_rule.rules]
}

# Eventbridge Cloudwatch Logs 
resource "aws_cloudwatch_log_group" "event_bus_logs" {
  name              = "/aws/events/${var.project_name}-event-bus"
  retention_in_days = 3 # adjust per env

  tags = {
    Project     = var.project_name
    Module      = "EventBridge"
    Environment = var.env
  }
}


resource "aws_cloudwatch_log_resource_policy" "eventbridge_log_policy" {
  policy_name = "${var.project_name}-eventbridge-log-policy"

  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = ["delivery.logs.amazonaws.com", "events.amazonaws.com"]
      }
      Action = [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
      Resource = "${aws_cloudwatch_log_group.event_bus_logs.arn}:*"
    }]
  })
}

# Add a Catch-All Rule + Log Target
resource "aws_cloudwatch_event_rule" "log_all_events" {
  name           = "${var.project_name}-log-all-events"
  event_bus_name = aws_cloudwatch_event_bus.custom_event_bus.name
  description    = "Catch-all rule to log every event to CloudWatch"

  event_pattern = jsonencode({
    source = [{ "prefix" = "" }] # source = ["your.source.name"]  # e.g. "com.myapp.orders" for specific logs
  })
}

resource "aws_cloudwatch_event_target" "log_target" {
  rule           = aws_cloudwatch_event_rule.log_all_events.name
  event_bus_name = aws_cloudwatch_event_bus.custom_event_bus.name
  target_id      = "cloudwatch-log-target"
  arn            = aws_cloudwatch_log_group.event_bus_logs.arn
}

# If you also want to replay events (useful for debugging or re-processing), add an archive:
resource "aws_cloudwatch_event_archive" "event_bus_archive" {
  name             = "${var.project_name}-event-archive"
  event_source_arn = aws_cloudwatch_event_bus.custom_event_bus.arn
  retention_days   = 3
}

output "permission_arn_map" {
  value = local.permission_arn_map
}

output "target_map" {
  value = local.target_map
}
