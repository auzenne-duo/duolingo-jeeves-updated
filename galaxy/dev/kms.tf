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
    payload = "AQICAHiv5congEi5VHdDF3fTx4DjYoVhEMedwW8dwYVWCwNFnwGG7AdA56xRdoY8BksP56lbAAAAdjB0BgkqhkiG9w0BBwagZzBlAgEAMGAGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMswvalebouW6f5kKUAgEQgDOG0FyQpucbikUSQwi4dWwHUJbt/ZIrweIU8BTZKQtdtULEcSjuq+3G2dE6jW4rsWgjGOU="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "s3-worker"
      environment = var.environment
    }
  }

  secret {
    name    = "zendesk_password"
    payload = "AQICAHiv5congEi5VHdDF3fTx4DjYoVhEMedwW8dwYVWCwNFnwEucUbkaFvPFTFIb+okmLfFAAAAfjB8BgkqhkiG9w0BBwagbzBtAgEAMGgGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMNflUlY+4Q1G/ZE48AgEQgDsgZ738EuK1uaa3Jfzp83Ptz5+ghku1pCgHnSpsvJ3OrXYqsFx5iBfLZ3JVA9ZPMSVUKpgwUozgZyH9lQ=="

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
    payload = "AQICAHiv5congEi5VHdDF3fTx4DjYoVhEMedwW8dwYVWCwNFnwFnuwaveyRmeLN4zTY2i+BwAAAAsTCBrgYJKoZIhvcNAQcGoIGgMIGdAgEAMIGXBgkqhkiG9w0BBwEwHgYJYIZIAWUDBAEuMBEEDJ1jwU75nJmmaa65awIBEIBqjG06sWKfatXIXnzmA7A3Gr1fx/URfTpwGiJ9yo6XAqWmyLx5EaloC40Jc7IVfDDJ71Aeu2EiFVzkdg8F8IhQOiumbOFituHMrlwWKb2l3ZeSAyOhuw7ehShcwi06uMxnRl13C/IXuOHPlg=="

    context = {
      product     = var.product
      service     = var.service
      subservice  = "worker-cron"
      environment = var.environment
    }
  }

  secret {
    name    = "jira_api_token_general"
    payload = "AQICAHiv5congEi5VHdDF3fTx4DjYoVhEMedwW8dwYVWCwNFnwE/QBkYWBSP5LQRzy/F9qs4AAAAdjB0BgkqhkiG9w0BBwagZzBlAgEAMGAGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMQIYef98Vy7VZDgSjAgEQgDOn23tnr4RUAgt843SiulNX7gh4dPvDc0lpydE2AciaPW3EFcijRayhcS9XVMgtgn4Tk5I="

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
