# The AWS region. This is normally us-east-1
provider "aws" {
  region = "us-east-1"

  default_tags {
    tags = {
      github-repo = var.github_repository
      pd-rotation = var.pagerduty_rotation
      team        = var.team
    }
  }
}

terraform {
  backend "s3" {
    bucket         = "infra-galaxy-state"
    key            = "duolingo/jeeves/prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = "true"
    dynamodb_table = "infra-galaxy-lock"
  }

  required_version = "1.5.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.0"
    }
    pagerduty = {
      source = "pagerduty/pagerduty"
    }
    sentry = {
      source  = "jianyuan/sentry"
      version = "~> 0.11.2"
    }
  }
}

# Create an internal service so that things stay behind the edge gateway.
# See: https://docs.google.com/document/d/1tU7y9wWsBFwdnWFkz0bEosU7U_8lxs4N7h4NJ80CqfU/edit
module "duolingo-jeeves-internal" {
  source                            = "app.terraform.io/duolingo/galaxy/terraform//modules/ecs_web_service"
  version                           = "~> 2.0"
  environment                       = var.environment
  service                           = var.service
  subservice                        = "internal"
  health_check_path                 = "/health"
  min_count                         = 2    # Minimum number of tasks to run in autoscaling group
  max_count                         = 5    # Maximum number of tasks to run in autoscaling group
  scale_out_cpu                     = 80   # Scale out at this cpu usage (percent)
  memory                            = 8192 # Maximum memory (default: 128MB)
  product                           = var.product
  owner                             = var.owner       # The name of the owner for this service
  ecs_cluster                       = var.ecs_cluster # Name of the ECS cluster to run on
  container_port                    = 5000
  internal                          = "true" # Create internal service. This handles traffic behind the edge gateway
  enable_http_listener              = "true"
  http_listener_type                = "redirect"
  release_version                   = var.release_version
  health_check_grace_period_seconds = 120
  # Essentially disables cloudwatch latency trigger here since we cannot filter out specific routes for this.
  # Latency alerts from Honeycomb is set up in https://ui.honeycomb.io/duolingo/environments/main/datasets/jeeves/triggers/r7rQMEAUzoR
  latency_threshold                    = 10000
  latency_threshold_evaluation_periods = 10


  environment_vars = [
    {
      name  = "JIRA_USERNAME"
      value = "jira-automation@duolingo.com"
    },
    {
      name  = "SHAKIRA_JIRA_USERNAME_IOS"
      value = "ios-shake-feedback@duolingo.com"
    },
    {
      name  = "SHAKIRA_JIRA_USERNAME_ANDROID"
      value = "android-shake-feedback@duolingo.com"
    },
    {
      name  = "SHAKIRA_JIRA_USERNAME_WEB"
      value = "jira-automation@duolingo.com"
    },
    {
      name  = "SHAKIRA_JIRA_USERNAME_LITERACY"
      value = "jira-automation@duolingo.com"
    },
    {
      name  = "SENTRY_DSN"
      value = data.sentry_key.sentry_dsn.dsn_public
    },
    {
      name  = "SENTRY_ENVIRONMENT"
      value = var.environment
    }
  ]

  warning_alarm_actions   = [aws_sns_topic.warning.arn]
  emergency_alarm_actions = [aws_sns_topic.warning.arn]

  doppler_secrets = [{
    doppler_key = "JIRA_API_TOKEN_GENERAL"
    env_var     = "JIRA_API_TOKEN"
    }, {
    doppler_key = "SHAKIRA_JIRA_API_TOKEN_IOS"
    env_var     = "SHAKIRA_JIRA_API_TOKEN_IOS"
    }, {
    doppler_key = "SHAKIRA_JIRA_API_TOKEN_ANDROID"
    env_var     = "SHAKIRA_JIRA_API_TOKEN_ANDROID"
    }, {
    doppler_key = "SHAKIRA_JIRA_API_TOKEN_WEB"
    env_var     = "SHAKIRA_JIRA_API_TOKEN_WEB"
    }, {
    doppler_key = "SHAKIRA_JIRA_API_TOKEN_LITERACY"
    env_var     = "SHAKIRA_JIRA_API_TOKEN_LITERACY"
    }, {
    doppler_key = "DUOLINGO_USERNAME"
    env_var     = "DUOLINGO_USERNAME"
    }, {
    doppler_key = "DUOLINGO_PASSWORD"
    env_var     = "DUOLINGO_PASSWORD"
    }, {
    doppler_key = "SHAKIRA_SLACK_API_TOKEN"
    env_var     = "SHAKIRA_SLACK_API_TOKEN"
  }]
}

module "duolingo-jeeves-s3-worker" {
  source                             = "app.terraform.io/duolingo/galaxy/terraform//modules/ecs_worker_service"
  version                            = "~> 2.0"
  environment                        = var.environment
  service                            = var.service
  subservice                         = "s3-worker"
  cpu                                = 4096
  memory                             = 1024
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
      name  = "JIRA_USERNAME"
      value = "jira-automation@duolingo.com"
    },
    {
      name  = "APPFIGURES_USER"
      value = "jeeves-automation@duolingo.com"
    },
    {
      name  = "REDDIT_CLIENT_ID"
      value = "cSp-H5vky827VpmP0fRVeA"
    },
    {
      name  = "REDDIT_USERNAME"
      value = "reddit-jeeves"
    },
    {
      name  = "SENTRY_DSN"
      value = data.sentry_key.sentry_dsn.dsn_public
    },
    {
      name  = "SENTRY_ENVIRONMENT"
      value = var.environment
    }
  ]

  release_version = var.release_version

  warning_alarm_actions   = [aws_sns_topic.warning.arn]
  emergency_alarm_actions = [aws_sns_topic.warning.arn]

  doppler_secrets = [{
    doppler_key = "JIRA_API_TOKEN"
    env_var     = "JIRA_API_TOKEN"
    }, {
    doppler_key = "APPFIGURES_PASSWORD"
    env_var     = "APPFIGURES_PASSWORD"
    }, {
    doppler_key = "APPFIGURES_CLIENT_KEY"
    env_var     = "APPFIGURES_CLIENT_KEY"
    }, {
    doppler_key = "REDDIT_SECRET_TOKEN"
    env_var     = "REDDIT_SECRET_TOKEN"
    }, {
    doppler_key = "REDDIT_PASSWORD"
    env_var     = "REDDIT_PASSWORD"
    }, {
    doppler_key = "DUOLINGO_USERNAME"
    env_var     = "DUOLINGO_USERNAME"
    }, {
    doppler_key = "DUOLINGO_PASSWORD"
    env_var     = "DUOLINGO_PASSWORD"
    }, {
    doppler_key = "ZENDESK_API_TOKEN"
    env_var     = "ZENDESK_API_TOKEN"
  }]
}

module "duolingo-jeeves-worker-cron" {
  source               = "app.terraform.io/duolingo/galaxy/terraform//modules/ecs_worker_service"
  version              = "~> 2.0"
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
  environment_vars = [
    {
      name  = "PYTHONPATH"
      value = "/code"
    },
  ]
  schedule_expression = "cron(0 9 * * ? *)"
  release_version     = var.release_version

  warning_alarm_actions   = [aws_sns_topic.warning.arn]
  emergency_alarm_actions = [aws_sns_topic.warning.arn]

  doppler_secrets = [{
    doppler_key = "BETA_FEEDBACK_SPIKE_REPORTER_SLACK_API_TOKEN"
    env_var     = "BETA_FEEDBACK_SPIKE_REPORTER_SLACK_API_TOKEN"
    }, {
    doppler_key = "BUG_SPIKE_REPORTER_SLACK_API_TOKEN"
    env_var     = "BUG_SPIKE_REPORTER_SLACK_API_TOKEN"
    }, {
    doppler_key = "SOCIAL_TRENDS_SPIKE_REPORTER_SLACK_API_TOKEN"
    env_var     = "SOCIAL_TRENDS_SPIKE_REPORTER_SLACK_API_TOKEN"
    }, {
    doppler_key = "SPIKE_REPORTER_SLACK_API_TOKEN"
    env_var     = "SPIKE_REPORTER_SLACK_API_TOKEN"
  }]
}

module "duolingo-jeeves-sqs-worker-1" {
  source                      = "app.terraform.io/duolingo/galaxy/terraform//modules/ecs_worker_service"
  version                     = "~> 2.0"
  environment                 = var.environment
  service                     = var.service
  subservice                  = "sqs-worker-1"
  cpu                         = 4096 # 1024 equals one core
  memory                      = 2048 # in MB
  min_count                   = 6    # Minimum number of tasks to run in autoscaling group
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
      name  = "ZENDESK_REPORTS_USER"
      value = "reports@duolingo.com"
    },
    {
      name  = "SENTRY_DSN"
      value = data.sentry_key.sentry_dsn.dsn_public
    },
    {
      name  = "SENTRY_ENVIRONMENT"
      value = var.environment
    }
  ]

  sqs_uri             = aws_sqs_queue.jeeves-pipeline-break-download-verify.id
  scale_out_sqs       = 250
  scale_out_count_sqs = 16

  warning_alarm_actions   = []
  emergency_alarm_actions = [aws_sns_topic.warning.arn]

  doppler_secrets = [{
    doppler_key = "JIRA_API_TOKEN_SQS_WORKER_1"
    env_var     = "JIRA_API_TOKEN"
    }, {
    doppler_key = "DUOLINGO_USERNAME"
    env_var     = "DUOLINGO_USERNAME"
    }, {
    doppler_key = "DUOLINGO_PASSWORD"
    env_var     = "DUOLINGO_PASSWORD"
    }, {
    doppler_key = "ZENDESK_API_TOKEN"
    env_var     = "ZENDESK_API_TOKEN"
  }]
}

module "duolingo-jeeves-sqs-worker-2" {
  source               = "app.terraform.io/duolingo/galaxy/terraform//modules/ecs_worker_service"
  version              = "~> 2.0"
  environment          = var.environment
  service              = var.service
  subservice           = "sqs-worker-2"
  cpu                  = 1024 # 1024 equals one core
  memory               = 4096 # in MB
  min_count            = 4    # Minimum number of tasks to run in autoscaling group
  max_count            = 20   # Maximum number of tasks to run in autoscaling group
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
    {
      name  = "SENTRY_DSN"
      value = data.sentry_key.sentry_dsn.dsn_public
    },
    {
      name  = "SENTRY_ENVIRONMENT"
      value = var.environment
    }
  ]

  sqs_uri             = aws_sqs_queue.jeeves-pipeline-break-verify-index.id
  scale_out_sqs       = 2000
  scale_out_count_sqs = 16

  warning_alarm_actions   = [aws_sns_topic.warning.arn]
  emergency_alarm_actions = [aws_sns_topic.warning.arn]


  doppler_secrets = [{
    doppler_key = "DUOLINGO_USERNAME"
    env_var     = "DUOLINGO_USERNAME"
    }, {
    doppler_key = "DUOLINGO_PASSWORD"
    env_var     = "DUOLINGO_PASSWORD"
  }]
}

module "duolingo-jeeves-spike-worker" {
  source               = "app.terraform.io/duolingo/galaxy/terraform//modules/ecs_worker_service"
  version              = "~> 2.0"
  environment          = var.environment
  service              = var.service
  subservice           = "spike-worker"
  cpu                  = 1024 # 1024 equals one core
  memory               = 8192 # in MB
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


  environment_vars = [
    {
      name  = "SENTRY_DSN"
      value = data.sentry_key.sentry_dsn.dsn_public
    },
    {
      name  = "SENTRY_ENVIRONMENT"
      value = var.environment
    }
  ]

  doppler_secrets = [{
    doppler_key = "DUOLINGO_USERNAME"
    env_var     = "DUOLINGO_USERNAME"
    }, {
    doppler_key = "DUOLINGO_PASSWORD"
    env_var     = "DUOLINGO_PASSWORD"
  }]
}

module "duolingo-jeeves-email-sender" {
  source               = "app.terraform.io/duolingo/galaxy/terraform//modules/ecs_worker_service"
  version              = "~> 2.0"
  environment          = var.environment
  service              = var.service
  subservice           = "email-sender"
  cpu                  = 256 # 1024 equals one core
  memory               = 512 # in MB
  min_count            = 1   # Minimum number of tasks to run in autoscaling group
  max_count            = 1   # Maximum number of tasks to run in autoscaling group
  product              = var.product
  owner                = var.owner       # The name of the owner for this service
  ecs_cluster          = var.ecs_cluster # Name of the ECS cluster to run on
  container_definition = "email-sender.json"
  schedule_expression  = "cron(0 16 ? * MON *)"
  release_version      = var.release_version

  warning_alarm_actions   = [aws_sns_topic.warning.arn]
  emergency_alarm_actions = [aws_sns_topic.warning.arn]
}

module "duolingo-jeeves-ensure-embeddings-worker" {
  source               = "app.terraform.io/duolingo/galaxy/terraform//modules/ecs_worker_service"
  version              = "~> 2.0"
  environment          = var.environment
  service              = var.service
  subservice           = "ensure-embeddings-worker"
  cpu                  = 1024 # 1024 equals one core
  memory               = 4096 # in MB
  min_count            = 1    # Minimum number of tasks to run in autoscaling group
  max_count            = 1    # Maximum number of tasks to run in autoscaling group
  product              = var.product
  owner                = var.owner       # The name of the owner for this service
  ecs_cluster          = var.ecs_cluster # Name of the ECS cluster on which to run
  container_definition = "ensure-embeddings-worker.json"
  schedule_expression  = "cron(0 11 ? * * *)"
  release_version      = var.release_version
  environment_vars = [
    {
      name  = "PYTHONPATH"
      value = "/code"
    },
    {
      name  = "SENTRY_DSN"
      value = data.sentry_key.sentry_dsn.dsn_public
    },
    {
      name  = "SENTRY_ENVIRONMENT"
      value = var.environment
    }
  ]


  doppler_secrets = [{
    doppler_key = "DUOLINGO_USERNAME"
    env_var     = "DUOLINGO_USERNAME"
    }, {
    doppler_key = "DUOLINGO_PASSWORD"
    env_var     = "DUOLINGO_PASSWORD"
  }]
}
