# Get the zone information for the vpc.duolingo.com domain
data "aws_route53_zone" "duolingo-vpc" {
  name = "vpc.duolingo.com."
}

resource "aws_route53_record" "duolingo-jeeves-memcache-vpc-record" {
  zone_id = data.aws_route53_zone.duolingo-vpc.zone_id
  name    = "duolingo-jeeves-memcache-prod.${data.aws_route53_zone.duolingo-vpc.name}"
  type    = "CNAME"
  records = [module.duolingo-jeeves-memcache.cluster_address]
  ttl     = "10"
}

module "duolingo-jeeves-memcache" {
  source          = "github.com/duolingo/infra-galaxy//modules/memcache_cluster"
  identifier      = "duolingo-jeeves-prod"
  product         = var.product
  owner           = var.owner
  service         = var.service
  subservice      = "memcache"
  environment     = var.environment
  node_type       = "cache.t2.small"
  num_cache_nodes = 3
}
