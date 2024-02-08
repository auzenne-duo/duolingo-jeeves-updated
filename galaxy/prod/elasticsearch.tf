# TODO (david.sawicki): Rename module to "jeeves-opensearch" once we upgrade to a higher version of OpenSearch
# TODO (david.sawicki): upgrade "elasticsearch_version" to "OpenSearch_1.3.10" and then "OpenSearch_2.7.0"
module "jeeves-elasticsearch" {
  source                = "app.terraform.io/duolingo/galaxy/terraform//modules/elasticsearch_domain"
  version               = "~> 1.0"
  elasticsearch_version = "7.7"
  product               = var.product
  service               = var.service
  subservice            = "es"
  owner                 = var.owner
  environment           = var.environment
  cluster_instance_type = "i3.2xlarge.elasticsearch"
}

data "aws_security_group" "duolingo-jeeves-es-prod-internal-esd" {
  name = "duolingo-jeeves-es-prod-internal-esd"
}

resource "aws_security_group_rule" "allow-vpn-ingress-https" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["10.0.0.0/8"]
  security_group_id = data.aws_security_group.duolingo-jeeves-es-prod-internal-esd.id
}
