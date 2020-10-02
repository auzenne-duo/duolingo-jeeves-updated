module "jeeves-elasticsearch" {
  source      = "github.com/duolingo/infra-galaxy//modules/elasticsearch_domain"
  product     = "${var.product}"
  service     = "${var.service}"
  subservice  = "es"
  owner       = "${var.owner}"
  environment = "${var.environment}"
}

data "aws_security_group" "duolingo-jeeves-es-dev-internal-esd" {
  name = "duolingo-jeeves-es-dev-internal-esd"
}

resource "aws_security_group_rule" "allow-vpn-ingress-https" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["10.0.0.0/8"]
  security_group_id = "${data.aws_security_group.duolingo-jeeves-es-dev-internal-esd.id}"
}
