/*
terraform console > module.sqs.queue_arns:
{
  "notification_events" = "arn:aws:sqs:af-south-1:157489943321:asset-transfer-notifications-queue"
  "transfer_approval_events" = "arn:aws:sqs:af-south-1:157489943321:asset-transfer-approval-queue"
  "transfer_receipt_events" = "arn:aws:sqs:af-south-1:157489943321:asset-transfer-receipt-queue"
  "transfer_request_events" = "arn:aws:sqs:af-south-1:157489943321:asset-transfer-request-queue"
  "transfer_transit_events" = "arn:aws:sqs:af-south-1:157489943321:asset-transfer-transit-queue"
}
*/
output "queue_arns" {
  description = "sqs queue arns, output example above"
  value = {
    for k, v in aws_sqs_queue.queue : k => v.arn
  }
}


output "queue_urls" {
  value = {
    for k, v in aws_sqs_queue.queue : k => v.id
  }
}

output "dlq_arns" {
  value = {
    for k, v in aws_sqs_queue.dlq : k => v.arn
  }
}
