resource "aws_kms_key" "kms_key" {
  description = "Key for encrypting/decrypting duolingo jeeves prod resources"

  tags {
    product     = "${var.product}"
    service     = "${var.service}"
    environment = "${var.environment}"
    owner       = "${var.owner}"
  }
}

resource "aws_kms_alias" "kms_alias" {
  name          = "alias/duolingo/jeeves/prod"
  target_key_id = "${aws_kms_key.kms_key.key_id}"
}

data "aws_kms_secrets" "secrets" {
  secret {
    name    = "zendesk_password"
    payload = "AQICAHjxaJXhk2UpReI01jpOgJrJbCY1xx4cyjZgCB9UDPIIZwH2eEAhkA/oaRSypwO6I6u9AAAAfjB8BgkqhkiG9w0BBwagbzBtAgEAMGgGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMu9kMbwBRqQkW0kGBAgEQgDvkmzo2M3HBLnk0xYvkPP/dcXEL9vqyP6GlZPChWZ55C/qAcGmVq6cQRGHw8kewX8jYB3QBk+z95zQFaA=="

    context {
      product     = "${var.product}"
      service     = "${var.service}"
      subservice  = "s3-worker"
      environment = "${var.environment}"
    }
  }
}
