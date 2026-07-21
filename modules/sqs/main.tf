// FIFO must be enabled for the SQS Queue

resource "aws_sqs_queue" "queue" {
  for_each = var.queues

  name = each.value.fifo ? "${each.value.name}.fifo" : each.value.name

  fifo_queue = try(each.value.fifo, false)

  visibility_timeout_seconds = try(each.value.visibility_timeout, 30)

  content_based_deduplication = try(each.value.fifo, false) ? try(each.value.content_deduplication, true) : null

  redrive_policy = try(each.value.create_dlq, true) ? jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq[each.key].arn
    maxReceiveCount     = try(each.value.max_receive_count, 3)
  }) : null

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}

resource "aws_sqs_queue" "dlq" {
  for_each = {
    for k, v in var.queues : k => v
    if try(v.create_dlq, true)
  }

  name = try(each.value.fifo, false) ? "${each.value.name}-dlq.fifo" : "${each.value.name}-dlq"

  fifo_queue = try(each.value.fifo, false)

  content_based_deduplication = try(each.value.fifo, false) ? try(each.value.content_deduplication, true) : null
}



// This connects SQS to Lambda Functions
resource "aws_lambda_event_source_mapping" "this" {
  for_each = var.sqs_lambda_triggers

  event_source_arn = aws_sqs_queue.queue[each.key].arn
  function_name    = each.value.function_name

  batch_size = try(each.value.batch_size, 10)
  enabled    = try(each.value.enabled, true)

  maximum_batching_window_in_seconds = try(each.value.maximum_batching_window_in_seconds, 0)
}

resource "aws_sqs_queue_policy" "policy" {
  for_each = var.queues

  queue_url = aws_sqs_queue.queue[each.key].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowEventBridgeSendMessage"
        Effect = "Allow"

        Principal = {
          Service = "events.amazonaws.com"
        }

        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.queue[each.key].arn
      }
    ]
  })
}
