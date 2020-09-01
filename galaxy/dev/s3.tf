data "aws_iam_policy_document" "s3-rw-duolingo-jeeves" {
  statement {
    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation",
    ]

    resources = ["arn:aws:s3:::duolingo-jeeves"]
  }

  statement {
    actions = [
      "s3:PutObject",
      "s3:PutObjectAcl",
      "s3:GetObject",
      "s3:GetObjectAcl",
    ]

    resources = ["arn:aws:s3:::duolingo-jeeves/*"]
  }
}

resource "aws_iam_role_policy" "s3-rw-duolingo-jeeves" {
  name = "s3-rw-duolingo-jeeves"
  role = "${module.duolingo-jeeves.iam_role}"

  policy = "${data.aws_iam_policy_document.s3-rw-duolingo-jeeves.json}"
}
