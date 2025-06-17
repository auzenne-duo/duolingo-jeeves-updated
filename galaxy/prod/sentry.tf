provider "sentry" {}

resource "sentry_project" "duolingo-jeeves" {
  organization = "duolingo-sentry"

  teams = var.pagerduty_rotation != "none" ? ["duolingo", var.pagerduty_rotation] : ["duolingo"]

  name = "duolingo-jeeves"
  slug = "duolingo-jeeves"

}

data "sentry_key" "sentry_dsn" {
  organization = "duolingo-sentry"
  project      = "duolingo-jeeves"

  name = "Default"

}
