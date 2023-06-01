data "aws_s3_bucket" "duolingo-jeeves" {
  bucket = "duolingo-jeeves"
}


data "aws_iam_policy_document" "s3-rw-duolingo-jeeves" {
  statement {
    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation",
    ]

    resources = [
      data.aws_s3_bucket.duolingo-jeeves.arn,
      aws_s3_bucket.jeeves-document-cache-dev.arn,
    ]
  }

  statement {
    actions = [
      "s3:PutObject",
      "s3:PutObjectAcl",
      "s3:GetObject",
      "s3:GetObjectAcl",
    ]

    resources = [
      "${data.aws_s3_bucket.duolingo-jeeves.arn}/*",
      "${aws_s3_bucket.jeeves-document-cache-dev.arn}/*"
    ]
  }

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

  statement {
    actions = [
      "sns:Publish",
    ]

    resources = [
      aws_sns_topic.jeeves-beta-feedback.arn,
    ]
  }
}

resource "aws_iam_role_policy" "s3-rw-duolingo-jeeves" {
  name = "s3-rw-duolingo-jeeves"
  role = module.duolingo-jeeves.iam_role

  policy = data.aws_iam_policy_document.s3-rw-duolingo-jeeves.json
}

resource "aws_iam_role_policy" "s3-rw-duolingo-jeeves-s3-worker" {
  name = "s3-rw-duolingo-jeeves"
  role = module.duolingo-jeeves-s3-worker.iam_role

  policy = data.aws_iam_policy_document.s3-rw-duolingo-jeeves.json
}

resource "aws_iam_role_policy" "s3-rw-duolingo-jeeves-spike-worker" {
  name = "s3-rw-duolingo-jeeves"
  role = module.duolingo-jeeves-spike-worker.iam_role

  policy = data.aws_iam_policy_document.s3-rw-duolingo-jeeves.json
}

resource "aws_iam_role_policy" "s3-rw-duolingo-jeeves-sqs-worker-1" {
  name = "s3-rw-duolingo-jeeves"
  role = module.duolingo-jeeves-sqs-worker-1.iam_role

  policy = data.aws_iam_policy_document.s3-rw-duolingo-jeeves.json
}

resource "aws_iam_role_policy" "s3-rw-duolingo-jeeves-sqs-worker-2" {
  name = "s3-rw-duolingo-jeeves"
  role = module.duolingo-jeeves-sqs-worker-2.iam_role

  policy = data.aws_iam_policy_document.s3-rw-duolingo-jeeves.json
}

resource "aws_iam_role_policy" "s3-rw-duolingo-jeeves-priority-estimator-updater" {
  name = "s3-rw-duolingo-jeeves"
  role = module.duolingo-jeeves-priority-estimator-updater.iam_role

  policy = data.aws_iam_policy_document.s3-rw-duolingo-jeeves.json
}
