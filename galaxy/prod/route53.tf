# Get the zone information for the duolingo.com domain
data "aws_route53_zone" "duolingo" {
  name = "duolingo.com."
}

resource "aws_route53_record" "duolingo-jeeves-prod" {
  zone_id = data.aws_route53_zone.duolingo.zone_id
  name    = "jeeves.${data.aws_route53_zone.duolingo.name}"
  type    = "A"

  alias {
    name                   = module.duolingo-jeeves.dns_name
    zone_id                = module.duolingo-jeeves.zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "duolingo-jeeves-prod-internal" {
  zone_id = data.aws_route53_zone.duolingo.zone_id
  name    = "jeeves-internal.${data.aws_route53_zone.duolingo.name}"
  type    = "A"

  alias {
    name                   = module.duolingo-jeeves-internal.dns_name
    zone_id                = module.duolingo-jeeves-internal.zone_id
    evaluate_target_health = false
  }
}
