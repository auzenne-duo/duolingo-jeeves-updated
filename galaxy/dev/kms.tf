resource "aws_kms_key" "kms-key" {
  description = "Key for encrypting/decrypting duolingo jeeves dev resources"

  tags = {
    product     = var.product
    service     = var.service
    environment = var.environment
    owner       = var.owner
  }
}

resource "aws_kms_alias" "kms-alias" {
  name          = "alias/duolingo/jeeves/dev"
  target_key_id = aws_kms_key.kms-key.key_id
}

data "aws_kms_secrets" "secrets" {
  secret {
    name    = "appfigures_client_key"
    payload = "AQICAHiv5congEi5VHdDF3fTx4DjYoVhEMedwW8dwYVWCwNFnwGSHcGgNffi21gigQgMED5CAAAAfjB8BgkqhkiG9w0BBwagbzBtAgEAMGgGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMOoo9fz0fm0NJI4RuAgEQgDsvjBQFRQ/bSZsjk7tV7SVce4tg/4s2BLYqWF1m0wOCHE27sNe7wmbp3SpagBmDB8+JYCn5SqIaO3TIZA=="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "s3-worker"
      environment = var.environment
    }
  }

  secret {
    name    = "appfigures_password"
    payload = "AQICAHiv5congEi5VHdDF3fTx4DjYoVhEMedwW8dwYVWCwNFnwFO/gYpEof/qsifU4Nqjp+oAAAAhjCBgwYJKoZIhvcNAQcGoHYwdAIBADBvBgkqhkiG9w0BBwEwHgYJYIZIAWUDBAEuMBEEDFwloN2s/FKbXJ1G9gIBEIBCRkPG1716O9FYwXNbFWOZ9YIWfC6TBk0Swvov0cNukMr+quGGW9+c4BL3L3qd2vzym7OM1Y5UX5rjkTxegeKHvUzz"

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
    name    = "jira_api_token"
    payload = "AQICAHi8VJKHFYAxFeUp4dS+8Aw/C0l5T9o3fMCTutWJlPq2MgF6bD6m4W6iINwMK7D21h8zAAAAdjB0BgkqhkiG9w0BBwagZzBlAgEAMGAGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMtPnd+oRk6hNorXb9AgEQgDPpQAHewoarnEDOdPN71/bREgBFruTQ6cHPc3AblIrUwUVxx6HrxQi4XMYvr/msu49eKjg="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "s3-worker"
      environment = var.environment
    }
  }

  secret {
    name    = "zendesk_password"
    payload = "AQICAHiv5congEi5VHdDF3fTx4DjYoVhEMedwW8dwYVWCwNFnwEP+oxpxEcPQCB1ltoB8ONgAAAAhjCBgwYJKoZIhvcNAQcGoHYwdAIBADBvBgkqhkiG9w0BBwEwHgYJYIZIAWUDBAEuMBEEDKJCVDNHFBSvWUgHQAIBEIBCShC5SuoaRI4ThTwnnjha0SY/vCF/JNOIoPoBKfxV0WiAFrrdjQEi+T92FjKiOd0jM4Cc/RwepQfX2dLwzvjdxxEJ"

    context = {
      product     = var.product
      service     = var.service
      subservice  = "s3-worker"
      environment = var.environment
    }
  }

  secret {
    name    = "jira_api_token_sqs_worker_1"
    payload = "AQICAHi8VJKHFYAxFeUp4dS+8Aw/C0l5T9o3fMCTutWJlPq2MgHDiHmiLY0qoWuz5b5znxJUAAAAdjB0BgkqhkiG9w0BBwagZzBlAgEAMGAGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMqDCNOphdVxyYi4o6AgEQgDOJWHjS246LgvbnpwrTMIRjgLbAjTSiFs+9f8BM4bu7I31b/ScYD4aN3veZX8txF4QhVqo="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "sqs-worker-1"
      environment = var.environment
    }
  }

  secret {
    name    = "spike_reporter_slack_api_token"
    payload = "AQICAHi8VJKHFYAxFeUp4dS+8Aw/C0l5T9o3fMCTutWJlPq2MgE9FpV3QQEmjdsrFueOHalZAAAAlzCBlAYJKoZIhvcNAQcGoIGGMIGDAgEAMH4GCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMFnB2drr+2Hcu8mAXAgEQgFExTRfSENr+8TaFkbCID3or87xq6EQBoq3+aafdxpp1PWyfyO2bcLRFMQVqnTU+UfoALPh3u/M+wUUMJ6E7bvCNficHrZa29SXauuwNix7Opzk="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "worker-cron"
      environment = var.environment
    }
  }

  secret {
    name    = "jira_api_token_general"
    payload = "AQICAHi8VJKHFYAxFeUp4dS+8Aw/C0l5T9o3fMCTutWJlPq2MgFkrNor5k3GY9kkgWSedg/sAAAAdjB0BgkqhkiG9w0BBwagZzBlAgEAMGAGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMGa0G3EGOkq+KDGvXAgEQgDPBBIqmILw6848rsaHaXezU7rngkK/goYERsxmBcMoRMQfJeK72YA9EFDNwsRJSaBerJ2w="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "api"
      environment = var.environment
    }
  }

  secret {
    name    = "shakira_jira_api_token_ios"
    payload = "AQICAHiv5congEi5VHdDF3fTx4DjYoVhEMedwW8dwYVWCwNFnwEjs//ej3AhdzKfd+vGHjMKAAAAdjB0BgkqhkiG9w0BBwagZzBlAgEAMGAGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMDjjVV1clfTMdEI8xAgEQgDMKdH1iUfwsi9vM+VTaaaZHEswu1Psgwrg02SB4SSRGX/+jMzb4Of+0htKcOKhbb28t0Hk="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "api"
      environment = var.environment
    }
  }

  secret {
    name    = "shakira_jira_api_token_android"
    payload = "AQICAHiv5congEi5VHdDF3fTx4DjYoVhEMedwW8dwYVWCwNFnwEDNc7x6vwWuLkO1JYbm/b1AAAAdjB0BgkqhkiG9w0BBwagZzBlAgEAMGAGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMIBpjg5oOmQsjcNcXAgEQgDOsxNST9bRhEaEsdIda6Bur1i3RFTFcF8u0nIgYV6vN+Lln1XHsxf6o7VQRo7UZpToAKJs="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "api"
      environment = var.environment
    }
  }

  secret {
    name    = "shakira_jira_api_token_web"
    payload = "AQICAHi8VJKHFYAxFeUp4dS+8Aw/C0l5T9o3fMCTutWJlPq2MgGOiCqHHFvGPen4ayiu5O6PAAAAdjB0BgkqhkiG9w0BBwagZzBlAgEAMGAGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMxOiN4kvRiMNt6FZEAgEQgDPmrKDpOuBLLvdrhASqQIo6Y/9EeK0oZF/ni97+6u8XqTezv4rGK2tcDSJDJca1ASoYng4="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "api"
      environment = var.environment
    }
  }

  secret {
    name    = "shakira_jira_api_token_literacy"
    payload = "AQICAHi8VJKHFYAxFeUp4dS+8Aw/C0l5T9o3fMCTutWJlPq2MgFfbYiw2wdUXXsBE9/Xx0sQAAAAdjB0BgkqhkiG9w0BBwagZzBlAgEAMGAGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMIWtiWXYqPD9HQ9etAgEQgDMTD0XZ3Np8OOSZnwg9zy2r7tJ0qIFsUH4XqJvdAxNq+2z+rMih1n4WGlSFCGqKMm2oDhA="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "api"
      environment = var.environment
    }
  }

  secret {
    name    = "shakira_slack_api_token"
    payload = "AQICAHiv5congEi5VHdDF3fTx4DjYoVhEMedwW8dwYVWCwNFnwGtuyA0bsqRbuPb4cbnYwFgAAAAlzCBlAYJKoZIhvcNAQcGoIGGMIGDAgEAMH4GCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQM8PhPSzTae40RU5wBAgEQgFFoThjbgOIhkJvC4ES3oKSVLOZniGNmK6C6E9B9pyDygKW/8RQRE3aPQF2d3aEoyrIiLtXICPHHINkBmgQVuaaof1riEWpe8qQ8ADhmhVUPFO4="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "api"
      environment = var.environment
    }
  }
}
