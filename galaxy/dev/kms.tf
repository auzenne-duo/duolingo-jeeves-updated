resource "aws_kms_key" "kms-key" {
  description = "Key for encrypting/decrypting duolingo jeeves dev resources"

  tags {
    product     = "${var.product}"
    service     = "${var.service}"
    environment = "${var.environment}"
    owner       = "${var.owner}"
  }
}

resource "aws_kms_alias" "kms-alias" {
  name          = "alias/duolingo/jeeves/dev"
  target_key_id = "${aws_kms_key.kms-key.key_id}"
}

data "aws_kms_secrets" "secrets" {
  secret {
    name    = "zendesk_password"
    payload = "AQICAHiv5congEi5VHdDF3fTx4DjYoVhEMedwW8dwYVWCwNFnwEucUbkaFvPFTFIb+okmLfFAAAAfjB8BgkqhkiG9w0BBwagbzBtAgEAMGgGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMNflUlY+4Q1G/ZE48AgEQgDsgZ738EuK1uaa3Jfzp83Ptz5+ghku1pCgHnSpsvJ3OrXYqsFx5iBfLZ3JVA9ZPMSVUKpgwUozgZyH9lQ=="

    context {
      product     = "${var.product}"
      service     = "${var.service}"
      subservice  = "s3-worker"
      environment = "${var.environment}"
    }
  }

  # We require that the URL of our Slack channel be encrypted because Slack provides no auth measures around webhooks, other than "don't give away the URL"
  secret {
    name    = "slack_post_url"
    payload = "AQICAHiv5congEi5VHdDF3fTx4DjYoVhEMedwW8dwYVWCwNFnwFnuwaveyRmeLN4zTY2i+BwAAAAsTCBrgYJKoZIhvcNAQcGoIGgMIGdAgEAMIGXBgkqhkiG9w0BBwEwHgYJYIZIAWUDBAEuMBEEDJ1jwU75nJmmaa65awIBEIBqjG06sWKfatXIXnzmA7A3Gr1fx/URfTpwGiJ9yo6XAqWmyLx5EaloC40Jc7IVfDDJ71Aeu2EiFVzkdg8F8IhQOiumbOFituHMrlwWKb2l3ZeSAyOhuw7ehShcwi06uMxnRl13C/IXuOHPlg=="

    context {
      product     = "${var.product}"
      service     = "${var.service}"
      subservice  = "worker-cron"
      environment = "${var.environment}"
    }
  }
}
