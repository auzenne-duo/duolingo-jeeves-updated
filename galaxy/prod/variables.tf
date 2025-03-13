variable "release_version" {
  description = "The version of the app to deploy"
}

variable "product" {
  default = "duolingo"
}

variable "service" {
  default = "jeeves"
}

variable "environment" {
  default = "prod"
}

variable "owner" {
  default = "david.sawicki@duolingo.com"
}

variable "ecs_cluster" {
  default = "prod"
}

variable "pagerduty_rotation" {
  default = "grizzly"
}

variable "github_repository" {
  default = "duolingo-jeeves"
}

variable "team" {
  default = "observability-team@duolingo.com"
}
