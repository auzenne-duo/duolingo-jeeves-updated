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

data "aws_kms_secret" "zendesk_password" {
  secret {
    name    = "zendesk_password"
    payload = "AQICAHjxaJXhk2UpReI01jpOgJrJbCY1xx4cyjZgCB9UDPIIZwHIzuDzUDFUCJ6vp2urjFmYAAAAbTBrBgkqhkiG9w0BBwagXjBcAgEAMFcGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMV+O3URWi15v6GkPbAgEQgCpXvYaa0XPXHqtEvcW60v/yjkMt1f1GZOpFUm3s3phD2I6jyl9cFF7NxC8="

    context {
      product     = "${var.product}"
      service     = "${var.service}"
      subservice  = "s3-worker"
      environment = "${var.environment}"
    }
  }
}
