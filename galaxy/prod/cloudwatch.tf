module "duolingo-jeeves-memcache-alarms" {
  source        = "github.com/duolingo/infra-galaxy//modules/memcache_alarms"
  alarm_actions = [aws_sns_topic.warning.arn]
  cluster_name  = module.duolingo-jeeves-memcache.cluster_id
  environment   = var.environment
  num_nodes     = "3"
  product       = var.product
  service       = var.service
}
