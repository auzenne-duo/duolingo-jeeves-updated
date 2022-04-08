# The AWS region. This is normally us-east-1
provider "aws" {
  region  = "us-east-1"
  version = "~> 3.0"
}

terraform {
  backend "s3" {
    bucket         = "infra-galaxy-state"
    key            = "duolingo/jeeves/prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = "true"
    dynamodb_table = "infra-galaxy-lock"
  }

  required_version = "0.12.31"
}

# Get the zone information for the duolingo.com domain
data "aws_route53_zone" "duolingo" {
  name = "duolingo.com."
}

resource "aws_route53_record" "duolingo-jeeves-prod" {
  zone_id = data.aws_route53_zone.duolingo.zone_id
  name    = "jeeves.${data.aws_route53_zone.duolingo.name}"
  type    = "A"

  alias {
    name                   = module.duolingo-jeeves.dns_name
    zone_id                = module.duolingo-jeeves.zone_id
    evaluate_target_health = false
  }
}

module "duolingo-jeeves" {
  source                            = "github.com/duolingo/infra-galaxy//modules/ecs_web_service"
  environment                       = var.environment
  service                           = var.service
  subservice                        = "api"
  health_check_path                 = "/health"
  min_count                         = 1    # Minimum number of tasks to run in autoscaling group
  max_count                         = 5    # Maximum number of tasks to run in autoscaling group
  scale_out_cpu                     = 80   # Scale out at this cpu usage (percent)
  memory                            = 4096 # Maximum memory (default: 128MB)
  product                           = var.product
  owner                             = var.owner       # The name of the owner for this service
  ecs_cluster                       = var.ecs_cluster # Name of the ECS cluster to run on
  container_port                    = 5000
  internal                          = "false" # Create a service accessible outside the office network
  enable_http_listener              = "true"
  http_listener_type                = "redirect"
  release_version                   = var.release_version
  health_check_grace_period_seconds = 120

  environment_vars = [
    {
      name  = "JIRA_USERNAME"
      value = "jira-automation@duolingo.com"
    },
    {
      name  = "JIRA_API_TOKEN"
      value = data.aws_kms_secrets.secrets.plaintext["jira_api_token_general"]
    },
    {
      name  = "SHAKIRA_SLACK_API_TOKEN"
      value = data.aws_kms_secrets.secrets.plaintext["shakira_slack_api_token"]
    },
    {
      name  = "SHAKIRA_JIRA_USERNAME_IOS"
      value = "ios-shake-feedback@duolingo.com"
    },
    {
      name  = "SHAKIRA_JIRA_API_TOKEN_IOS"
      value = data.aws_kms_secrets.secrets.plaintext["shakira_jira_api_token_ios"]
    },
    {
      name  = "SHAKIRA_JIRA_USERNAME_ANDROID"
      value = "android-shake-feedback@duolingo.com"
    },
    {
      name  = "SHAKIRA_JIRA_API_TOKEN_ANDROID"
      value = data.aws_kms_secrets.secrets.plaintext["shakira_jira_api_token_android"]
    },
    {
      name  = "SHAKIRA_JIRA_USERNAME_WEB"
      value = "jira-automation@duolingo.com"
    },
    {
      name  = "SHAKIRA_JIRA_API_TOKEN_WEB"
      value = data.aws_kms_secrets.secrets.plaintext["shakira_jira_api_token_web"]
    },
  ]

  warning_alarm_actions   = [aws_sns_topic.warning.arn]
  emergency_alarm_actions = [aws_sns_topic.warning.arn]
}

module "duolingo-jeeves-s3-worker" {
  source                             = "github.com/duolingo/infra-galaxy//modules/ecs_worker_service"
  environment                        = var.environment
  service                            = var.service
  subservice                         = "s3-worker"
  cpu                                = 1024
  memory                             = 4096
  min_count                          = 1 # Minimum number of tasks to run in autoscaling group
  max_count                          = 1 # Maximum number of tasks to run in autoscaling group
  scale_out_count                    = 0
  deployment_minimum_healthy_percent = 0
  product                            = var.product
  owner                              = var.owner       # The name of the owner for this service
  ecs_cluster                        = var.ecs_cluster # Name of the ECS cluster to run on
  container_definition               = "s3-worker.json"

  environment_vars = [
    {
      name  = "PYTHONPATH"
      value = "/code"
    },
    {
      name  = "ZENDESK_USER"
      value = "jeeves-automation@duolingo.com"
    },
    {
      name  = "ZENDESK_PASSWORD"
      value = data.aws_kms_secrets.secrets.plaintext["zendesk_password"]
    },
    {
      name  = "JIRA_USERNAME"
      value = "jira-automation@duolingo.com"
    },
    {
      name  = "JIRA_API_TOKEN"
      value = data.aws_kms_secrets.secrets.plaintext["jira_api_token"]
    },
    {
      name  = "APPFIGURES_USER"
      value = "jeeves-automation@duolingo.com"
    },
    {
      name  = "APPFIGURES_PASSWORD"
      value = data.aws_kms_secrets.secrets.plaintext["appfigures_password"]
    },
    {
      name  = "APPFIGURES_CLIENT_KEY"
      value = data.aws_kms_secrets.secrets.plaintext["appfigures_client_key"]
    },
  ]

  release_version = var.release_version

  warning_alarm_actions   = [aws_sns_topic.warning.arn]
  emergency_alarm_actions = [aws_sns_topic.warning.arn]
}

module "duolingo-jeeves-worker-cron" {
  source               = "github.com/duolingo/infra-galaxy//modules/ecs_worker_service"
  environment          = var.environment
  service              = var.service
  subservice           = "worker-cron"
  cpu                  = 256 # 1024 equals one core
  memory               = 512 # in MB
  min_count            = 1   # Minimum number of tasks to run in autoscaling group
  max_count            = 1   # Maximum number of tasks to run in autoscaling group
  product              = var.product
  owner                = var.owner       # The name of the owner for this service
  ecs_cluster          = var.ecs_cluster # Name of the ECS cluster to run on
  container_definition = "worker-cron.json"
  cookie_secret        = data.aws_kms_secrets.secrets.plaintext["spike_reporter_slack_api_token"]
  schedule_expression  = "cron(0 9 * * ? *)"
  release_version      = var.release_version

  warning_alarm_actions   = [aws_sns_topic.warning.arn]
  emergency_alarm_actions = [aws_sns_topic.warning.arn]
}

module "duolingo-jeeves-sqs-worker-1" {
  source                      = "github.com/duolingo/infra-galaxy//modules/ecs_worker_service"
  environment                 = var.environment
  service                     = var.service
  subservice                  = "sqs-worker-1"
  cpu                         = 1024 # 1024 equals one core
  memory                      = 4096 # in MB
  min_count                   = 1    # Minimum number of tasks to run in autoscaling group
  max_count                   = 40   # Maximum number of tasks to run in autoscaling group
  product                     = var.product
  owner                       = var.owner       # The name of the owner for this service
  ecs_cluster                 = var.ecs_cluster # Name of the ECS cluster to run on
  container_definition        = "sqs-worker-1.json"
  release_version             = var.release_version
  scale_in_evaluation_periods = 5



  environment_vars = [
    {
      name  = "PYTHONPATH"
      value = "/code"
    },
    {
      name  = "JIRA_USERNAME"
      value = "jira-automation@duolingo.com"
    },
    {
      name  = "JIRA_API_TOKEN"
      value = data.aws_kms_secrets.secrets.plaintext["jira_api_token_sqs_worker_1"]
    },
  ]

  sqs_uri             = aws_sqs_queue.jeeves-pipeline-break-download-verify.id
  scale_out_sqs       = 250
  scale_out_count_sqs = 16

  warning_alarm_actions   = []
  emergency_alarm_actions = [aws_sns_topic.warning.arn]
}

module "duolingo-jeeves-sqs-worker-2" {
  source               = "github.com/duolingo/infra-galaxy//modules/ecs_worker_service"
  environment          = var.environment
  service              = var.service
  subservice           = "sqs-worker-2"
  cpu                  = 1024 # 1024 equals one core
  memory               = 4096 # in MB
  min_count            = 1    # Minimum number of tasks to run in autoscaling group
  max_count            = 8    # Maximum number of tasks to run in autoscaling group
  product              = var.product
  owner                = var.owner       # The name of the owner for this service
  ecs_cluster          = var.ecs_cluster # Name of the ECS cluster to run on
  container_definition = "sqs-worker-2.json"
  release_version      = var.release_version

  environment_vars = [
    {
      name  = "PYTHONPATH"
      value = "/code"
    },
  ]

  sqs_uri             = aws_sqs_queue.jeeves-pipeline-break-verify-index.id
  scale_out_sqs       = 2500
  scale_out_count_sqs = 16

  warning_alarm_actions   = [aws_sns_topic.warning.arn]
  emergency_alarm_actions = [aws_sns_topic.warning.arn]
}

module "duolingo-jeeves-spike-worker" {
  source               = "github.com/duolingo/infra-galaxy//modules/ecs_worker_service"
  environment          = var.environment
  service              = var.service
  subservice           = "spike-worker"
  cpu                  = 1024 # 1024 equals one core
  memory               = 4096 # in MB
  min_count            = 1    # Minimum number of tasks to run in autoscaling group
  max_count            = 1    # Maximum number of tasks to run in autoscaling group
  product              = var.product
  owner                = var.owner       # The name of the owner for this service
  ecs_cluster          = var.ecs_cluster # Name of the ECS cluster to run on
  container_definition = "spike-worker.json"
  schedule_expression  = "rate(15 minutes)"
  release_version      = var.release_version

  warning_alarm_actions   = [aws_sns_topic.warning.arn]
  emergency_alarm_actions = [aws_sns_topic.warning.arn]
}
