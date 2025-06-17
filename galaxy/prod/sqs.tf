resource "aws_sqs_queue" "jeeves-attachments" {
  name                       = "jeeves-attachments"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 345600
  max_message_size           = 262144
  delay_seconds              = 0
  receive_wait_time_seconds  = 0
  redrive_policy             = "{\"deadLetterTargetArn\":\"${aws_sqs_queue.jeeves-attachments-deadletter.arn}\",\"maxReceiveCount\":5}"

  tags = {
    product     = var.product
    service     = var.service
    environment = var.environment
  }

}

resource "aws_sqs_queue" "jeeves-attachments-deadletter" {
  name                       = "jeeves-attachments-deadletter"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 345600
  max_message_size           = 262144
  delay_seconds              = 0
  receive_wait_time_seconds  = 0

  tags = {
    product     = var.product
    service     = var.service
    environment = var.environment
  }

}

data "aws_iam_policy_document" "sqs-rw-jeeves-attachments" {
  statement {
    actions = [
      "sqs:ListQueues",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
      "sqs:ListDeadLetterSourceQueues",
      "sqs:ReceiveMessage",
      "sqs:ChangeMessageVisibility",
      "sqs:ChangeMessageVisibilityBatch",
      "sqs:DeleteMessage",
      "sqs:DeleteMessageBatch",
      "sqs:PurgeQueue",
      "sqs:SendMessage",
      "sqs:SendMessageBatch",
    ]

    resources = [
      aws_sqs_queue.jeeves-attachments.arn,
      aws_sqs_queue.jeeves-attachments-deadletter.arn,
    ]
  }
}

resource "aws_sqs_queue" "jeeves-pipeline-break-download-verify" {
  name                       = "jeeves-pipeline-break-download-verify"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 345600
  max_message_size           = 262144
  delay_seconds              = 0
  receive_wait_time_seconds  = 0
  redrive_policy             = "{\"deadLetterTargetArn\":\"${aws_sqs_queue.jeeves-pipeline-break-download-verify-deadletter.arn}\",\"maxReceiveCount\":5}"

  tags = {
    product     = var.product
    service     = var.service
    environment = var.environment
  }

}

resource "aws_sqs_queue" "jeeves-pipeline-break-download-verify-deadletter" {
  name                       = "jeeves-pipeline-break-download-verify-deadletter"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 345600
  max_message_size           = 262144
  delay_seconds              = 0
  receive_wait_time_seconds  = 0

  tags = {
    product     = var.product
    service     = var.service
    environment = var.environment
  }

}

resource "aws_sqs_queue" "jeeves-pipeline-break-verify-index" {
  name                       = "jeeves-pipeline-break-verify-index"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 345600
  max_message_size           = 262144
  delay_seconds              = 0
  receive_wait_time_seconds  = 0
  redrive_policy             = "{\"deadLetterTargetArn\":\"${aws_sqs_queue.jeeves-pipeline-break-verify-index-deadletter.arn}\",\"maxReceiveCount\":5}"

  tags = {
    product     = var.product
    service     = var.service
    environment = var.environment
  }

}

resource "aws_sqs_queue" "jeeves-pipeline-break-verify-index-deadletter" {
  name                       = "jeeves-pipeline-break-verify-index-deadletter"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 345600
  max_message_size           = 262144
  delay_seconds              = 0
  receive_wait_time_seconds  = 0

  tags = {
    product     = var.product
    service     = var.service
    environment = var.environment
  }

}
