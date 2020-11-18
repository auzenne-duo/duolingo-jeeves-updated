resource "aws_kms_key" "kms-key" {
  description = "Key for encrypting/decrypting duolingo jeeves prod resources"

  tags = {
    product     = var.product
    service     = var.service
    environment = var.environment
    owner       = var.owner
  }
}

resource "aws_kms_alias" "kms-alias" {
  name          = "alias/duolingo/jeeves/prod"
  target_key_id = aws_kms_key.kms-key.key_id
}

data "aws_kms_secrets" "secrets" {
  secret {
    name    = "appfigures_client_key"
    payload = "AQICAHjxaJXhk2UpReI01jpOgJrJbCY1xx4cyjZgCB9UDPIIZwECL4pDFfGBTN237rDPcE+VAAAAfjB8BgkqhkiG9w0BBwagbzBtAgEAMGgGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMdOfV2eD20rlgIwHUAgEQgDu2wF/woHXir5yNfThVE03Xj12upT1oeqUFmtUKOD9sthZKRDiDjyn31wV/Fbi2FATkhk9iXH5isHwA2Q=="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "s3-worker"
      environment = var.environment
    }
  }

  secret {
    name    = "appfigures_password"
    payload = "AQICAHjxaJXhk2UpReI01jpOgJrJbCY1xx4cyjZgCB9UDPIIZwEQSZiaBmUfm4PWo+DdqFjTAAAAhjCBgwYJKoZIhvcNAQcGoHYwdAIBADBvBgkqhkiG9w0BBwEwHgYJYIZIAWUDBAEuMBEEDCvX+KD+LGYLD3MONAIBEIBCZXmW0trLt8/XldGNaGC504xHUqigqDgzGEb64OQAMz2qDfehlGPzvpkSwkbXiLVkxaHeOGU4EVf47v/2Hg7GHwc4"

    context = {
      product     = var.product
      service     = var.service
      subservice  = "s3-worker"
      environment = var.environment
    }
  }

  secret {
    name    = "jira_api_token"
    payload = "AQICAHjxaJXhk2UpReI01jpOgJrJbCY1xx4cyjZgCB9UDPIIZwG/lV9PAyLMFnjmGAWXy+JfAAAAdjB0BgkqhkiG9w0BBwagZzBlAgEAMGAGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMCJe0tPa5AQmS810TAgEQgDMssZXbaKzXeHbTquYx2K7PNpl+WYTkPhUz9bvvepc8JXQd2wuLu63XZDypPCq3jY3/ndM="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "s3-worker"
      environment = var.environment
    }
  }

  secret {
    name    = "shakira_jira_api_token"
    payload = "AQICAHjxaJXhk2UpReI01jpOgJrJbCY1xx4cyjZgCB9UDPIIZwHd7Kk+uo7xPInUBljvWAhlAAAAdjB0BgkqhkiG9w0BBwagZzBlAgEAMGAGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMiFiLVJjpHZ0AyYCcAgEQgDOPqsyFinZ56WU89rfjC5x1d0cmlBwwZj5pJKk+NFGxfAKPLIf16vnQXavIL7xsg4RVGzY="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "api"
      environment = var.environment
    }
  }

  secret {
    name    = "zendesk_password"
    payload = "AQICAHjxaJXhk2UpReI01jpOgJrJbCY1xx4cyjZgCB9UDPIIZwH2eEAhkA/oaRSypwO6I6u9AAAAfjB8BgkqhkiG9w0BBwagbzBtAgEAMGgGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMu9kMbwBRqQkW0kGBAgEQgDvkmzo2M3HBLnk0xYvkPP/dcXEL9vqyP6GlZPChWZ55C/qAcGmVq6cQRGHw8kewX8jYB3QBk+z95zQFaA=="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "s3-worker"
      environment = var.environment
    }
  }

  # We require that the URL of our Slack channel be encrypted because Slack provides no auth measures around webhooks, other than "don't give away the URL"
  secret {
    name    = "slack_post_url"
    payload = "AQICAHjxaJXhk2UpReI01jpOgJrJbCY1xx4cyjZgCB9UDPIIZwHWkUiHVZPJmoiEgCl/GpF4AAAAsTCBrgYJKoZIhvcNAQcGoIGgMIGdAgEAMIGXBgkqhkiG9w0BBwEwHgYJYIZIAWUDBAEuMBEEDB8LRikx7ODBwOlYYAIBEIBq/C8pHAcPgLiVwM2zGwsmyCzHzNNY8WJ3vu5z1u2qBu0zP09pbYFbv7Ya5TuoXM/Ob41FRD2GnwUfF4zjXtj9F/QN0xGEd7xZJ61zwi9m6BSR6Pc6RCOe64X2wNPjZRE6KFK3CTi/WuoW8Q=="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "worker-cron"
      environment = var.environment
    }
  }

  secret {
    name    = "shake_to_report_jira_token"
    payload = "AQICAHjxaJXhk2UpReI01jpOgJrJbCY1xx4cyjZgCB9UDPIIZwFejsjh7t1n8efszcFP+qmuAAAAdjB0BgkqhkiG9w0BBwagZzBlAgEAMGAGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMemAzuE+3jcnRGJrrAgEQgDPq0DV8ZBG0wVhNHAbATnC48Y+gQXe4R+IDtWrwBJuDE3j95qPz5JqtDWQ8TSC8KtKy31o="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "api"
      environment = var.environment
    }
  }

  secret {
    name    = "shake_to_report_slack_token"
    payload = "AQICAHjxaJXhk2UpReI01jpOgJrJbCY1xx4cyjZgCB9UDPIIZwFI1e5Lsx5tLcUcoumub4s0AAAAlzCBlAYJKoZIhvcNAQcGoIGGMIGDAgEAMH4GCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMv+VqTnIT6MdE486GAgEQgFFvmuUTcdVcpiLq8SX3rCG4oYV8uCHzRDwNN4cQWiCilEkABkV4+GSLXDx/2xidYJ8lviIwfUnqgZpDCoRk3U2dUxOjPT2xw/OGJaSxrAQmGnM="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "api"
      environment = var.environment
    }
  }
}
