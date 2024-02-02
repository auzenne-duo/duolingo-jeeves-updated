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
    name    = "zendesk_reports_password"
    payload = "AQICAHjxaJXhk2UpReI01jpOgJrJbCY1xx4cyjZgCB9UDPIIZwHrzmihYdVvNS2kUfdRUiolAAAAcTBvBgkqhkiG9w0BBwagYjBgAgEAMFsGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMPwlhIOnCXSiD3XJHAgEQgC5H2mjcxIH3mX82cliJfQAdStEKvdVZNPOuSW8kCdgnppbL1CMtoVTd4AJiF/c6"

    context = {
      product     = var.product
      service     = var.service
      subservice  = "sqs-worker-1"
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
    name    = "bug_spike_reporter_slack_api_token"
    payload = "AQICAHjxaJXhk2UpReI01jpOgJrJbCY1xx4cyjZgCB9UDPIIZwFSDQDryRNqfiG84Xzw3P63AAAAlzCBlAYJKoZIhvcNAQcGoIGGMIGDAgEAMH4GCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMdiml5JQbnSOcXXPKAgEQgFE2JLKpPfX744Ym3sfguDYTsiyLST2LMXxV4uShiOhw6yYjbGHHnC1ixWivfn0hr0LRU1yFhRXrUKgMLO3gquAKatVre4j0ZfBB3pxGtRYnJLk="
    context = {
      product     = var.product
      service     = var.service
      subservice  = "worker-cron"
      environment = var.environment
    }
  }

  secret {
    name    = "social_trends_spike_reporter_slack_api_token"
    payload = "AQICAHjxaJXhk2UpReI01jpOgJrJbCY1xx4cyjZgCB9UDPIIZwHfn4Qi0n8JnaFo5jE7QDADAAAAlzCBlAYJKoZIhvcNAQcGoIGGMIGDAgEAMH4GCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMk6INDk6QRwoqve5IAgEQgFGshcE5wdYQDtc94VO3ylmj8wcQcIQG3hoQRDNXQEEUqU3SK0ZER2Iu/noMBA4PLiSjNGaWzhlq1LFS/EAsEXxkrnCAu8Tmg6jYfFm6GIStWxE="
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
    name    = "priority_estimator_updater_jira_api_token"
    payload = "AQICAHjxaJXhk2UpReI01jpOgJrJbCY1xx4cyjZgCB9UDPIIZwEDU1SWeulmqTAk8LXrTXjUAAAAdjB0BgkqhkiG9w0BBwagZzBlAgEAMGAGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMhQWNh9px+4yg+jQyAgEQgDMv1+7W4j8iwfgmlpkCCz8bj4sIZzzbjYpU4qV+ajKitum7Pv2auNJV8Eko7UsPf7N9uQE="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "priority-estimator-updater"
      environment = var.environment
    }
  }
}
