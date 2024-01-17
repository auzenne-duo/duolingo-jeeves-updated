provider "sentry" {}

data "sentry_key" "sentry_dsn" {
  organization = "duolingo-sentry"
  project      = "duolingo-jeeves"

  name = "Default"

}
