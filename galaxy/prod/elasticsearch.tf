module "jeeves-elasticsearch" {
  source      = "github.com/duolingo/infra-galaxy//modules/elasticsearch_domain"
  product     = "${var.product}"
  service     = "${var.service}"
  subservice  = "es"
  owner       = "${var.owner}"
  environment = "${var.environment}"
}
