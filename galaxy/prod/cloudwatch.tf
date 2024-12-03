module "duolingo-jeeves-memcache-alarms" {
  source        = "app.terraform.io/duolingo/galaxy/terraform//modules/memcache_alarms"
  version       = "~> 2.0"
  alarm_actions = [aws_sns_topic.warning.arn]
  cluster_name  = module.duolingo-jeeves-memcache.cluster_id
  environment   = var.environment
  num_nodes     = "3"
  product       = var.product
  service       = var.service
}
