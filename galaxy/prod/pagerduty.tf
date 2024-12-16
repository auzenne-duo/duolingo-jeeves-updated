# See https://www.terraform.io/docs/providers/pagerduty/index.html
# for reference.

# Placeholder variable for the PagerDuty token. Do not modify!
variable "pagerduty_token" {
}

provider "pagerduty" {
  token = var.pagerduty_token
}

data "pagerduty_escalation_policy" "escalation-policy" {
  name = var.pagerduty_rotation
}

resource "pagerduty_service" "service" {
  name                 = "${var.product}-${var.service}"
  escalation_policy    = data.pagerduty_escalation_policy.escalation-policy.id
  auto_resolve_timeout = 14400

  acknowledgement_timeout = 1800
  alert_creation          = "create_alerts_and_incidents"

  incident_urgency_rule {
    type    = "constant"
    urgency = "high"
  }
}

resource "pagerduty_service" "service-low" {
  name                 = "${var.product}-${var.service}-low"
  escalation_policy    = data.pagerduty_escalation_policy.escalation-policy.id
  auto_resolve_timeout = 14400

  acknowledgement_timeout = 1800
  alert_creation          = "create_alerts_and_incidents"

  incident_urgency_rule {
    type    = "constant"
    urgency = "low"
  }
}

resource "aws_sns_topic_subscription" "pagerduty" {
  topic_arn              = aws_sns_topic.emergency.arn
  protocol               = "https"
  endpoint               = "https://events.pagerduty.com/integration/${pagerduty_service_integration.cloudwatch.integration_key}/enqueue"
  endpoint_auto_confirms = "true"
}

resource "aws_sns_topic_subscription" "pagerduty-low" {
  topic_arn              = aws_sns_topic.warning.arn
  protocol               = "https"
  endpoint               = "https://events.pagerduty.com/integration/${pagerduty_service_integration.cloudwatch-low.integration_key}/enqueue"
  endpoint_auto_confirms = "true"
}

# Vendor configuration and integration

# CloudWatch
data "pagerduty_vendor" "cloudwatch" {
  name = "Cloudwatch"
}

resource "pagerduty_service_integration" "cloudwatch" {
  name    = data.pagerduty_vendor.cloudwatch.name
  service = pagerduty_service.service.id
  vendor  = data.pagerduty_vendor.cloudwatch.id
}

resource "pagerduty_service_integration" "cloudwatch-low" {
  name    = data.pagerduty_vendor.cloudwatch.name
  service = pagerduty_service.service-low.id
  vendor  = data.pagerduty_vendor.cloudwatch.id
}

# Pingdom
data "pagerduty_vendor" "pingdom" {
  name = "pingdom"
}

resource "pagerduty_service_integration" "pingdom" {
  name    = data.pagerduty_vendor.pingdom.name
  service = pagerduty_service.service.id
  vendor  = data.pagerduty_vendor.pingdom.id
}

# Slack
data "pagerduty_vendor" "slack" {
  name = "Slack"
}

resource "pagerduty_service_integration" "slack" {
  name    = data.pagerduty_vendor.slack.name
  service = pagerduty_service.service.id
  vendor  = data.pagerduty_vendor.slack.id
}

# Zabbix
data "pagerduty_vendor" "zabbix" {
  name = "zabbix"
}

resource "pagerduty_service_integration" "zabbix" {
  name    = data.pagerduty_vendor.zabbix.name
  service = pagerduty_service.service.id
  vendor  = data.pagerduty_vendor.zabbix.id
}
