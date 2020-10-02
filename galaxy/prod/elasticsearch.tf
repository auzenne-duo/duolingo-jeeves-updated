module "jeeves-elasticsearch" {
  source                = "github.com/duolingo/infra-galaxy//modules/elasticsearch_domain?ref=ops-16711"
  elasticsearch_version = "7.7"
  product               = var.product
  service               = var.service
  subservice            = "es"
  owner                 = var.owner
  environment           = var.environment
}
