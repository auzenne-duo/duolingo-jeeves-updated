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
}

# Get the zone information for the duolingo.com domain
data "aws_route53_zone" "duolingo" {
  name = "duolingo.com."
}

resource "aws_route53_record" "duolingo-jeeves-dev" {
  zone_id = "${data.aws_route53_zone.duolingo.zone_id}"
  name    = "duolingo-jeeves-dev.${data.aws_route53_zone.duolingo.name}"
  type    = "A"

  alias {
    name                   = "${module.duolingo-jeeves.dns_name}"
    zone_id                = "${module.duolingo-jeeves.zone_id}"
    evaluate_target_health = false
  }
}

module "duolingo-jeeves" {
  source            = "github.com/duolingo/infra-galaxy//modules/ecs_web_service"
  environment       = "${var.environment}"
  service           = "${var.service}"
  subservice        = "api"
  health_check_path = "/health"
  min_count         = 1                                                           # Minimum number of tasks to run in autoscaling group
  max_count         = 1                                                           # Maximum number of tasks to run in autoscaling group
  memory            = 800                                                         # Maximum memory (default: 128MB)
  product           = "${var.product}"
  owner             = "${var.owner}"                                              # The name of the owner for this service
  ecs_cluster       = "${var.ecs_cluster}"                                        # Name of the ECS cluster to run on
  container_port    = 5000
  internal          = "true"                                                      # Create an internal service
  version           = "${var.version}"
}
