resource "aws_s3_bucket" "duolingo-jeeves" {
  bucket = "duolingo-jeeves"

  tags {
    product     = "${var.product}"
    service     = "${var.service}"
    environment = "${var.environment}"
    owner       = "${var.owner}"
  }
}

data "aws_iam_policy_document" "s3-rw-duolingo-jeeves" {
  statement {
    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation",
    ]

    resources = ["${aws_s3_bucket.duolingo-jeeves.arn}"]
  }

  statement {
    actions = [
      "s3:PutObject",
      "s3:PutObjectAcl",
      "s3:GetObject",
      "s3:GetObjectAcl",
    ]

    resources = ["${aws_s3_bucket.duolingo-jeeves.arn}/*"]
  }
}

resource "aws_iam_role_policy" "s3-rw-duolingo-jeeves" {
  name = "s3-rw-duolingo-jeeves"
  role = "${module.duolingo-jeeves.iam_role}"

  policy = "${data.aws_iam_policy_document.s3-rw-duolingo-jeeves.json}"
}

resource "aws_iam_role_policy" "s3-rw-duolingo-jeeves-worker" {
  name = "s3-rw-duolingo-jeeves"
  role = "${module.duolingo-jeeves-s3-worker.iam_role}"

  policy = "${data.aws_iam_policy_document.s3-rw-duolingo-jeeves.json}"
}
