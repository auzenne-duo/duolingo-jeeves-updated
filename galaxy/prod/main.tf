# The AWS region. This is normally us-east-1
provider "aws" {
  region = "us-east-1"
}

terraform {
  backend "s3" {
    bucket     = "infra-galaxy-state"
    key        = "duolingo/jeeves/prod/terraform.tfstate"
    region     = "us-east-1"
    encrypt    = "true"
    lock_table = "infra-galaxy-lock"
  }
}

# Get the zone information for the duolingo.com domain
data "aws_route53_zone" "duolingo" {
  name = "duolingo.com."
}

resource "aws_route53_record" "duolingo-jeeves-prod" {
  zone_id = "${data.aws_route53_zone.duolingo.zone_id}"
  name    = "jeeves.${data.aws_route53_zone.duolingo.name}"
  type    = "A"

  alias {
    name                   = "${module.duolingo-jeeves.dns_name}"
    zone_id                = "${module.duolingo-jeeves.zone_id}"
    evaluate_target_health = false
  }
}

module "duolingo-jeeves" {
  source         = "github.com/duolingo/infra-galaxy//modules/ecs_web_service"
  environment    = "${var.environment}"
  service        = "${var.service}"
  subservice     = "api"
  min_count      = 1                                                           # Minimum number of tasks to run in autoscaling group
  max_count      = 5                                                           # Maximum number of tasks to run in autoscaling group
  scale_out_cpu  = 80                                                          # Scale out at this cpu usage (percent)
  memory         = 768                                                         # Maximum memory (default: 128MB)
  product        = "${var.product}"
  owner          = "${var.owner}"                                              # The name of the owner for this service
  ecs_cluster    = "${var.ecs_cluster}"                                        # Name of the ECS cluster to run on
  container_port = 5000
  internal       = "true"                                                      # Create an internal service
  version        = "${var.version}"
}
