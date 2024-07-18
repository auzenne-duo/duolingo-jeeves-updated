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
    name    = "bug_spike_reporter_slack_api_token"
    payload = "AQICAHi8VJKHFYAxFeUp4dS+8Aw/C0l5T9o3fMCTutWJlPq2MgGs9MsuYeyeU2OhbZhzPNs8AAAAlzCBlAYJKoZIhvcNAQcGoIGGMIGDAgEAMH4GCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMsvT755PfQEU1IxXMAgEQgFE1/D93ESBYwcr3jiYLrNbHRFG5SoBmqPUNMY4S/v97F1/lQpNyzehwYQk+OzvL8Y43pLk1tA9+g4yfM5mknSDWikqnorfBjAerJazmle3/tUU="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "worker-cron"
      environment = var.environment
    }
  }

  secret {
    name    = "social_trends_spike_reporter_slack_api_token"
    payload = "AQICAHi8VJKHFYAxFeUp4dS+8Aw/C0l5T9o3fMCTutWJlPq2MgGGImnuWix28fk6NwnfluwzAAAAlzCBlAYJKoZIhvcNAQcGoIGGMIGDAgEAMH4GCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMfAiw6oh/1GFhGSFTAgEQgFG3gdramtxEcoYbkGPILDRzAqvfSnZkm68qjqUO3kwiyy2g/ljp7C8Ds2t/2Fypn9Y1FAG743gSzkM3ff7ElQopRB4unmpZ/oA5wau5v8QL+RU="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "worker-cron"
      environment = var.environment
    }
  }

  secret {
    name    = "beta_feedback_spike_reporter_slack_api_token"
    payload = "AQICAHi8VJKHFYAxFeUp4dS+8Aw/C0l5T9o3fMCTutWJlPq2MgHFQkD+4uwGBvsNvkkD89KeAAAAlzCBlAYJKoZIhvcNAQcGoIGGMIGDAgEAMH4GCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMWXMMLb/TUo2W80fWAgEQgFEvABT35w7X5xB7JCAXvtG6D1V/31fTZ1VyvjDNasIY6Js+Crx4BP7RmDH7HUFnke1QqCSTTz2LI3VUS0gQb6q970UxPil3jBIqN7nSgJ9wSX0="

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

}
