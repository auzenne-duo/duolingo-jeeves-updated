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
    payload = "AQICAHjxaJXhk2UpReI01jpOgJrJbCY1xx4cyjZgCB9UDPIIZwFVsgckWdEYO/k3w3Z6GK4cAAAAdjB0BgkqhkiG9w0BBwagZzBlAgEAMGAGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMXts7dbTRYH7/FFERAgEQgDNMFuyDR18db/mXILGw73JR4DhJE+XRm5fp8V2/nCLIN5JkDAfG5pgIEQh8w4FlHHQzBAQ="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "s3-worker"
      environment = var.environment
    }
  }

  secret {
    name    = "google-credentials-info"
    payload = "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"
    context = {
      product     = var.product
      service     = var.service
      subservice  = "worker"
      environment = var.environment
    }
  }

  secret {
    name    = "zendesk_password"
    payload = "AQICAHjxaJXhk2UpReI01jpOgJrJbCY1xx4cyjZgCB9UDPIIZwGeN5hzipINGtrGAClN7sLyAAAAhjCBgwYJKoZIhvcNAQcGoHYwdAIBADBvBgkqhkiG9w0BBwEwHgYJYIZIAWUDBAEuMBEEDDLXkUHYjaGacbISKAIBEIBCkAMAeNAUdOtW97Q4DGj9JBhIZuW5TTr+o65XHJ+8a2W+XVlKYMWMtWLTB79xwxgBF52nr3mPbYfcpkqKRGGXlIPT"

    context = {
      product     = var.product
      service     = var.service
      subservice  = "s3-worker"
      environment = var.environment
    }
  }

  secret {
    name    = "jira_api_token_sqs_worker_1"
    payload = "AQICAHjxaJXhk2UpReI01jpOgJrJbCY1xx4cyjZgCB9UDPIIZwGSroLp/9augXbYZgl8zilVAAAAdjB0BgkqhkiG9w0BBwagZzBlAgEAMGAGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQM8DhUs6mtuU6t+pp6AgEQgDOMret+w3cUJdGIxNZ1DF6M33cXjcYlYEJMpI0GzFNUshh3XvLxm37AJSoF5PW1wYLAfbE="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "sqs-worker-1"
      environment = var.environment
    }
  }

  secret {
    name    = "spike_reporter_slack_api_token"
    payload = "AQICAHjxaJXhk2UpReI01jpOgJrJbCY1xx4cyjZgCB9UDPIIZwEVDtJ8wrdQ0BkiC1D9lt83AAAAlzCBlAYJKoZIhvcNAQcGoIGGMIGDAgEAMH4GCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQM1L5m4jx9OxcuTo/AAgEQgFGQ6gleZSkfP8tYzPiZSBrmgU+3G78WHf48xzQoSC+Lz4aztSxnrmwJu6Z8Rx3IkhrfZmk2XAI0b9hbJHNSOCv9kAw4aBoEFWOrOLyr0YTlal4="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "worker-cron"
      environment = var.environment
    }
  }

  secret {
    name    = "jira_api_token_general"
    payload = "AQICAHjxaJXhk2UpReI01jpOgJrJbCY1xx4cyjZgCB9UDPIIZwGF4Rs/x+5wCCINFWME6nK5AAAAdjB0BgkqhkiG9w0BBwagZzBlAgEAMGAGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMiDeHXnHzjUw8ovP+AgEQgDO2j4R/waWaYJew3T+OoqeVICvphbrrvTy4AMt9SrQ0gg9E4H6NhzR9S6N+m+iYEWKCrHo="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "api"
      environment = var.environment
    }
  }

  secret {
    name    = "shakira_jira_api_token_ios"
    payload = "AQICAHjxaJXhk2UpReI01jpOgJrJbCY1xx4cyjZgCB9UDPIIZwFejsjh7t1n8efszcFP+qmuAAAAdjB0BgkqhkiG9w0BBwagZzBlAgEAMGAGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMemAzuE+3jcnRGJrrAgEQgDPq0DV8ZBG0wVhNHAbATnC48Y+gQXe4R+IDtWrwBJuDE3j95qPz5JqtDWQ8TSC8KtKy31o="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "api"
      environment = var.environment
    }
  }

  secret {
    name    = "shakira_jira_api_token_android"
    payload = "AQICAHjxaJXhk2UpReI01jpOgJrJbCY1xx4cyjZgCB9UDPIIZwGvo8zMo7Uwu/h7+Z9czIxgAAAAdjB0BgkqhkiG9w0BBwagZzBlAgEAMGAGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMkPpve/vevHKWccWzAgEQgDOh5HBrNrgIieXQcndYjQ1j6sF/hXuasoS23B6FGbYk+FugHM/8nS7C2Xd7GYaJy5JbEjs="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "api"
      environment = var.environment
    }
  }

  secret {
    name    = "shakira_jira_api_token_web"
    payload = "AQICAHjxaJXhk2UpReI01jpOgJrJbCY1xx4cyjZgCB9UDPIIZwHcXCp2IBj/OljHwnR4/TPlAAAAdjB0BgkqhkiG9w0BBwagZzBlAgEAMGAGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQM7/I3vh9zQFbCy6zOAgEQgDNJsWFGQQnXWy1G48bG7Joi9Bj2oLP2PgEwbjJXg+Nrbql1R6IPb2aCPnd/lIP7lnSjrVg="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "api"
      environment = var.environment
    }
  }

  secret {
    name    = "shakira_jira_api_token_literacy"
    payload = "AQICAHjxaJXhk2UpReI01jpOgJrJbCY1xx4cyjZgCB9UDPIIZwHKnzfnS1RLzYLA9f5p7ZieAAAAdjB0BgkqhkiG9w0BBwagZzBlAgEAMGAGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMHucySkSW/QvX6vWjAgEQgDNcz0uuxFNZIG6Be99JkEk4PcFkH4hucCZWjXEDBHajZIeabZeHXp0HW5kaPfj/tJGPWgs="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "api"
      environment = var.environment
    }
  }

  secret {
    name    = "shakira_slack_api_token"
    payload = "AQICAHjxaJXhk2UpReI01jpOgJrJbCY1xx4cyjZgCB9UDPIIZwFI1e5Lsx5tLcUcoumub4s0AAAAlzCBlAYJKoZIhvcNAQcGoIGGMIGDAgEAMH4GCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMv+VqTnIT6MdE486GAgEQgFFvmuUTcdVcpiLq8SX3rCG4oYV8uCHzRDwNN4cQWiCilEkABkV4+GSLXDx/2xidYJ8lviIwfUnqgZpDCoRk3U2dUxOjPT2xw/OGJaSxrAQmGnM="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "api"
      environment = var.environment
    }
  }
}
