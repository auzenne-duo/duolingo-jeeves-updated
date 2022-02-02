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
