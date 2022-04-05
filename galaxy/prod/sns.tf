# Warning and emergency SNS topics for alerting

resource "aws_sns_topic" "emergency" {
  name = "${var.product}-${var.service}-emergency"
}

resource "aws_sns_topic" "warning" {
  name = "${var.product}-${var.service}-warning"
}
