variable "queues" {
  type = map(object({
    name = string
    fifo = optional(bool, false)

    visibility_timeout = optional(number, 30)
    max_receive_count  = optional(number, 3)
    create_dlq         = optional(bool, true)

    content_deduplication = optional(bool, true)
  }))
}

variable "sqs_lambda_triggers" {
  type = map(object({
    function_name                      = string
    batch_size                         = optional(number, 10)
    enabled                            = optional(bool, true)
    maximum_batching_window_in_seconds = optional(number, 0)
  }))
  default = {}
}
