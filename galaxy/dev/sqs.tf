resource "aws_sqs_queue" "jeeves-attachments-dev" {
  name                       = "jeeves-attachments-dev"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 345600
  max_message_size           = 262144
  delay_seconds              = 0
  receive_wait_time_seconds  = 0
  redrive_policy             = "{\"deadLetterTargetArn\":\"${aws_sqs_queue.jeeves-attachments-deadletter-dev.arn}\",\"maxReceiveCount\":5}"


  tags = {
    product     = var.product
    service     = var.service
    environment = var.environment
    owner       = var.owner
  }

}

resource "aws_sqs_queue" "jeeves-attachments-deadletter-dev" {
  name                       = "jeeves-attachments-deadletter-dev"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 345600
  max_message_size           = 262144
  delay_seconds              = 0
  receive_wait_time_seconds  = 0


  tags = {
    product     = var.product
    service     = var.service
    environment = var.environment
    owner       = var.owner
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
      aws_sqs_queue.jeeves-attachments-dev.arn,
      aws_sqs_queue.jeeves-attachments-deadletter-dev.arn,
    ]
  }
}

resource "aws_sqs_queue" "jeeves-pipeline-break-download-verify-dev" {
  name                       = "jeeves-pipeline-break-download-verify-dev"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 345600
  max_message_size           = 262144
  delay_seconds              = 0
  receive_wait_time_seconds  = 0
  redrive_policy             = "{\"deadLetterTargetArn\":\"${aws_sqs_queue.jeeves-pipeline-break-download-verify-deadletter-dev.arn}\",\"maxReceiveCount\":5}"


  tags = {
    product     = var.product
    service     = var.service
    environment = var.environment
    owner       = var.owner
  }

}

resource "aws_sqs_queue" "jeeves-pipeline-break-download-verify-deadletter-dev" {
  name                       = "jeeves-pipeline-break-download-verify-deadletter-dev"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 345600
  max_message_size           = 262144
  delay_seconds              = 0
  receive_wait_time_seconds  = 0


  tags = {
    product     = var.product
    service     = var.service
    environment = var.environment
    owner       = var.owner
  }

}

resource "aws_sqs_queue" "jeeves-pipeline-break-verify-index-dev" {
  name                       = "jeeves-pipeline-break-verify-index-dev"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 345600
  max_message_size           = 262144
  delay_seconds              = 0
  receive_wait_time_seconds  = 0
  redrive_policy             = "{\"deadLetterTargetArn\":\"${aws_sqs_queue.jeeves-pipeline-break-verify-index-deadletter-dev.arn}\",\"maxReceiveCount\":5}"


  tags = {
    product     = var.product
    service     = var.service
    environment = var.environment
    owner       = var.owner
  }

}

resource "aws_sqs_queue" "jeeves-pipeline-break-verify-index-deadletter-dev" {
  name                       = "jeeves-pipeline-break-verify-index-deadletter-dev"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 345600
  max_message_size           = 262144
  delay_seconds              = 0
  receive_wait_time_seconds  = 0


  tags = {
    product     = var.product
    service     = var.service
    environment = var.environment
    owner       = var.owner
  }

}

data "aws_iam_policy_document" "sqs-rw-jeeves-pipeline-break" {
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
      aws_sqs_queue.jeeves-pipeline-break-download-verify-dev.arn,
      aws_sqs_queue.jeeves-pipeline-break-download-verify-deadletter-dev.arn,
      aws_sqs_queue.jeeves-pipeline-break-verify-index-dev.arn,
      aws_sqs_queue.jeeves-pipeline-break-verify-index-deadletter-dev.arn,
    ]
  }
}
