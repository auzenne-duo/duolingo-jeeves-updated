resource "aws_iam_role_policy" "s3-rw-duolingo-jeeves" {
  name = "s3-rw-duolingo-jeeves"
  role = "${module.duolingo-jeeves.iam_role}"

  policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": [
        "arn:aws:s3:::duolingo-jeeves"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectAcl",
        "s3:GetObject",
        "s3:GetObjectAcl"
      ],
      "Resource": [
        "arn:aws:s3:::duolingo-jeeves/*"
      ]
    }
  ]
}
POLICY
}
