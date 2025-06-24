provider "grafana" {
  url = var.grafana_url
}

# The AWS region. This is normally us-east-1.
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
    key            = "duolingo/jeeves/dev/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = "true"
    dynamodb_table = "infra-galaxy-lock"
  }

  required_version = "1.5.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    sentry = {
      source  = "jianyuan/sentry"
      version = "~> 0.11.2"
    }

    grafana = {
      source  = "grafana/grafana"
      version = "~> 3.0"
    }
  }
}

# Get the zone information for the duolingo.com domain
data "aws_route53_zone" "duolingo" {
  name = "duolingo.com."
}

resource "aws_route53_record" "duolingo-jeeves-dev" {
  zone_id = data.aws_route53_zone.duolingo.zone_id
  name    = "duolingo-jeeves-dev.${data.aws_route53_zone.duolingo.name}"
  type    = "A"

  alias {
    name                   = module.duolingo-jeeves.dns_name
    zone_id                = module.duolingo-jeeves.zone_id
    evaluate_target_health = false
  }
}

module "duolingo-jeeves" {
  source                            = "app.terraform.io/duolingo/galaxy/terraform//modules/ecs_web_service"
  version                           = "~> 3.0"
  environment                       = var.environment
  service                           = var.service
  subservice                        = "api"
  health_check_path                 = "/health"
  min_count                         = 1    # Minimum number of tasks to run in autoscaling group
  max_count                         = 1    # Maximum number of tasks to run in autoscaling group
  memory                            = 4096 # Maximum memory (default: 128MB)
  product                           = var.product
  ecs_cluster                       = var.ecs_cluster # Name of the ECS cluster to run on
  instance_types                    = var.instance_types
  container_port                    = 5000
  internal                          = "true" # Create an internal service
  health_check_grace_period_seconds = 120

  environment_vars = [
    {
      name  = "JIRA_USERNAME"
      value = "it@duolingo.com"
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
      value = "it@duolingo.com"
    },
    {
      name  = "SHAKIRA_JIRA_USERNAME_LITERACY"
      value = "it@duolingo.com"
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
    doppler_key = "IT_EMAIL_TOKEN"
    env_var     = "JIRA_API_TOKEN"
    }, {
    doppler_key = "SHAKIRA_JIRA_API_TOKEN_IOS"
    env_var     = "SHAKIRA_JIRA_API_TOKEN_IOS"
    }, {
    doppler_key = "SHAKIRA_JIRA_API_TOKEN_ANDROID"
    env_var     = "SHAKIRA_JIRA_API_TOKEN_ANDROID"
    }, {
    doppler_key = "IT_EMAIL_TOKEN"
    env_var     = "SHAKIRA_JIRA_API_TOKEN_WEB"
    }, {
    doppler_key = "IT_EMAIL_TOKEN"
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
  version                            = "~> 3.0"
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
  ecs_cluster                        = var.ecs_cluster # Name of the ECS cluster to run on
  instance_types                     = var.instance_types
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
      value = "it@duolingo.com"
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
    },
    {
      name  = "SHAKIRA_JIRA_USERNAME_IOS"
      value = "ios-shake-feedback@duolingo.com"
    },
    {
      name  = "SHAKIRA_JIRA_USERNAME_ANDROID"
      value = "android-shake-feedback@duolingo.com"
    }
  ]

  doppler_secrets = [{
    doppler_key = "IT_EMAIL_TOKEN"
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
    doppler_key = "ZENDESK_API_TOKEN"
    env_var     = "ZENDESK_API_TOKEN"
    }, {
    doppler_key = "DUOLINGO_USERNAME"
    env_var     = "DUOLINGO_USERNAME"
    }, {
    doppler_key = "DUOLINGO_PASSWORD"
    env_var     = "DUOLINGO_PASSWORD"
    }, {
    doppler_key = "SHAKIRA_JIRA_API_TOKEN_IOS"
    env_var     = "SHAKIRA_JIRA_API_TOKEN_IOS"
    }, {
    doppler_key = "SHAKIRA_JIRA_API_TOKEN_ANDROID"
    env_var     = "SHAKIRA_JIRA_API_TOKEN_ANDROID"
  }]
}

module "duolingo-jeeves-worker-cron" {
  source               = "app.terraform.io/duolingo/galaxy/terraform//modules/ecs_worker_service"
  version              = "~> 3.0"
  environment          = var.environment
  service              = var.service
  subservice           = "worker-cron"
  cpu                  = 256 # 1024 equals one core
  memory               = 512 # in MB
  min_count            = 1   # Minimum number of tasks to run in autoscaling group
  max_count            = 1   # Maximum number of tasks to run in autoscaling group
  product              = var.product
  ecs_cluster          = var.ecs_cluster # Name of the ECS cluster to run on
  instance_types       = var.instance_types
  container_definition = "worker-cron.json"
  environment_vars = [
    {
      name  = "PYTHONPATH"
      value = "/code"
    },
  ]
  schedule_expression = "cron(* * * * ? 1970)" # "cron(0/20 * * * ? *)"

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
  source               = "app.terraform.io/duolingo/galaxy/terraform//modules/ecs_worker_service"
  version              = "~> 3.0"
  environment          = var.environment
  service              = var.service
  subservice           = "sqs-worker-1"
  cpu                  = 4096 # 1024 equals one core
  memory               = 4096 # in MB
  min_count            = 1    # Minimum number of tasks to run in autoscaling group
  max_count            = 8    # Maximum number of tasks to run in autoscaling group
  product              = var.product
  ecs_cluster          = var.ecs_cluster # Name of the ECS cluster to run on
  instance_types       = var.instance_types
  container_definition = "sqs-worker-1.json"

  environment_vars = [
    {
      name  = "PYTHONPATH"
      value = "/code"
    },
    {
      name  = "JIRA_USERNAME"
      value = "it@duolingo.com"
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

  sqs_uri             = aws_sqs_queue.jeeves-pipeline-break-download-verify-dev.id
  scale_out_sqs       = 250
  scale_out_count_sqs = 16

  doppler_secrets = [{
    doppler_key = "IT_EMAIL_TOKEN"
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
  version              = "~> 3.0"
  environment          = var.environment
  service              = var.service
  subservice           = "sqs-worker-2"
  cpu                  = 1024 # 1024 equals one core
  memory               = 4096 # in MB
  min_count            = 1    # Minimum number of tasks to run in autoscaling group
  max_count            = 8    # Maximum number of tasks to run in autoscaling group
  product              = var.product
  ecs_cluster          = var.ecs_cluster # Name of the ECS cluster to run on
  instance_types       = var.instance_types
  container_definition = "sqs-worker-2.json"

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

  sqs_uri             = aws_sqs_queue.jeeves-pipeline-break-verify-index-dev.id
  scale_out_sqs       = 2500
  scale_out_count_sqs = 16

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
  version              = "~> 3.0"
  environment          = var.environment
  service              = var.service
  subservice           = "spike-worker"
  cpu                  = 1024 # 1024 equals one core
  memory               = 4096 # in MB
  min_count            = 1    # Minimum number of tasks to run in autoscaling group
  max_count            = 1    # Maximum number of tasks to run in autoscaling group
  product              = var.product
  ecs_cluster          = var.ecs_cluster # Name of the ECS cluster to run on
  instance_types       = var.instance_types
  container_definition = "spike-worker.json"
  schedule_expression  = "rate(15 minutes)"

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

# this task should never run in dev
module "duolingo-jeeves-email-sender" {
  source               = "app.terraform.io/duolingo/galaxy/terraform//modules/ecs_worker_service"
  version              = "~> 3.0"
  environment          = var.environment
  service              = var.service
  subservice           = "email-sender"
  cpu                  = 256 # 1024 equals one core
  memory               = 512 # in MB
  min_count            = 1   # Minimum number of tasks to run in autoscaling group
  max_count            = 1   # Maximum number of tasks to run in autoscaling group
  product              = var.product
  ecs_cluster          = var.ecs_cluster # Name of the ECS cluster to run on
  instance_types       = var.instance_types
  container_definition = "email-sender.json"
  schedule_expression  = "cron(* * * * ? 1970)" # "cron(0/20 * * * ? *)"
}

module "duolingo-jeeves-ensure-embeddings-worker" {
  source               = "app.terraform.io/duolingo/galaxy/terraform//modules/ecs_worker_service"
  version              = "~> 3.0"
  environment          = var.environment
  service              = var.service
  subservice           = "ensure-embeddings-worker"
  cpu                  = 1024 # 1024 equals one core
  memory               = 4096 # in MB
  min_count            = 1    # Minimum number of tasks to run in autoscaling group
  max_count            = 1    # Maximum number of tasks to run in autoscaling group
  product              = var.product
  ecs_cluster          = var.ecs_cluster # Name of the ECS cluster to run on
  instance_types       = var.instance_types
  container_definition = "ensure-embeddings-worker.json"
  schedule_expression  = "cron(0 17 ? * * *)"
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
