resource "aws_s3_bucket" "jeeves-document-cache-dev" {
  bucket = "jeeves-document-cache-dev"

  tags = {
    product     = var.product
    service     = var.service
    environment = var.environment
    owner       = var.owner
  }
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
}

resource "aws_iam_role_policy" "s3-rw-duolingo-jeeves" {
  name = "s3-rw-duolingo-jeeves"
  role = module.duolingo-jeeves.iam_role

  policy = data.aws_iam_policy_document.s3-rw-duolingo-jeeves.json
}

data "aws_s3_bucket" "duolingo-jeeves" {
  bucket = "duolingo-jeeves"
}
