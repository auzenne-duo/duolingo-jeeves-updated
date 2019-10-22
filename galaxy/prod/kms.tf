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
    payload = "AQICAHjxaJXhk2UpReI01jpOgJrJbCY1xx4cyjZgCB9UDPIIZwHAZU0RybaDDfhI9Dy33hZOAAAAcDBuBgkqhkiG9w0BBwagYTBfAgEAMFoGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMQNkTNEhe9pJsSxWDAgEQgC2kfEOdjNld6edxFXAmRUBcsBSygPLPSJqu7UZxmCpKt21lLzQnesUBllipp54="

    context {
      product     = "${var.product}"
      service     = "${var.service}"
      subservice  = "s3-worker"
      environment = "${var.environment}"
    }
  }
}
