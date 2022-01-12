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
