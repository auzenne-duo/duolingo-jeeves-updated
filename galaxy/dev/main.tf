# The AWS region. This is normally us-east-1
provider "aws" {
  region  = "us-east-1"
  version = "~> 2.0"
}

terraform {
  backend "s3" {
    bucket         = "infra-galaxy-state"
    key            = "duolingo/jeeves/dev/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = "true"
    dynamodb_table = "infra-galaxy-lock"
  }

  required_version = "0.12.29"
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
  source                            = "github.com/duolingo/infra-galaxy//modules/ecs_web_service?ref=ops-16711"
  environment                       = var.environment
  service                           = var.service
  subservice                        = "api"
  health_check_path                 = "/health"
  min_count                         = 1    # Minimum number of tasks to run in autoscaling group
  max_count                         = 1    # Maximum number of tasks to run in autoscaling group
  memory                            = 4096 # Maximum memory (default: 128MB)
  product                           = var.product
  owner                             = var.owner       # The name of the owner for this service
  ecs_cluster                       = var.ecs_cluster # Name of the ECS cluster to run on
  container_port                    = 5000
  internal                          = "true" # Create an internal service
  release_version                   = var.release_version
  health_check_grace_period_seconds = 120
}

module "duolingo-jeeves-s3-worker" {
  source                             = "github.com/duolingo/infra-galaxy//modules/ecs_worker_service?ref=ops-16711"
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
      value = "community-team@duolingo.com"
    },
    {
      name  = "ZENDESK_PASSWORD"
      value = data.aws_kms_secrets.secrets.plaintext["zendesk_password"]
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
}

module "duolingo-jeeves-worker-cron" {
  source               = "github.com/duolingo/infra-galaxy//modules/ecs_worker_service?ref=ops-16711"
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
  cookie_secret        = data.aws_kms_secrets.secrets.plaintext["slack_post_url"]
  schedule_expression  = "cron(* * * * ? 1970)"
  release_version      = var.release_version
}
