# Get the zone information for the vpc.duolingo.com domain
data "aws_route53_zone" "duolingo-vpc" {
  name = "vpc.duolingo.com."
}

resource "aws_route53_record" "duolingo-jeeves-memcache-vpc-record" {
  zone_id = data.aws_route53_zone.duolingo-vpc.zone_id
  name    = "duolingo-jeeves-memcache-dev.${data.aws_route53_zone.duolingo-vpc.name}"
  type    = "CNAME"
  records = [module.duolingo-jeeves-memcache.cluster_address]
  ttl     = "10"
}

module "duolingo-jeeves-memcache" {
  source             = "app.terraform.io/duolingo/galaxy/terraform//modules/memcache_cluster"
  version            = "~> 2.0"
  identifier         = "duolingo-jeeves-dev"
  product            = var.product
  owner              = var.owner
  service            = var.service
  subservice         = "memcache"
  engine_family      = "memcached1.6"
  engine_version     = "1.6.17"
  environment        = var.environment
  node_type          = "cache.t4g.medium"
  num_cache_nodes    = 3
  office_cidr_blocks = var.office_cidr_blocks
}
