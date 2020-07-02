resource "aws_kms_key" "kms-key" {
  description = "Key for encrypting/decrypting duolingo jeeves prod resources"

  tags {
    product     = "${var.product}"
    service     = "${var.service}"
    environment = "${var.environment}"
    owner       = "${var.owner}"
  }
}

resource "aws_kms_alias" "kms-alias" {
  name          = "alias/duolingo/jeeves/prod"
  target_key_id = "${aws_kms_key.kms-key.key_id}"
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

  # We require that the URL of our Slack channel be encrypted because Slack provides no auth measures around webhooks, other than "don't give away the URL"
  secret {
    name    = "slack_post_url"
    payload = "AQICAHjxaJXhk2UpReI01jpOgJrJbCY1xx4cyjZgCB9UDPIIZwHWkUiHVZPJmoiEgCl/GpF4AAAAsTCBrgYJKoZIhvcNAQcGoIGgMIGdAgEAMIGXBgkqhkiG9w0BBwEwHgYJYIZIAWUDBAEuMBEEDB8LRikx7ODBwOlYYAIBEIBq/C8pHAcPgLiVwM2zGwsmyCzHzNNY8WJ3vu5z1u2qBu0zP09pbYFbv7Ya5TuoXM/Ob41FRD2GnwUfF4zjXtj9F/QN0xGEd7xZJ61zwi9m6BSR6Pc6RCOe64X2wNPjZRE6KFK3CTi/WuoW8Q=="

    context {
      product     = "${var.product}"
      service     = "${var.service}"
      subservice  = "worker-cron"
      environment = "${var.environment}"
    }
  }
}
