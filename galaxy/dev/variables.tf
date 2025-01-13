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
  default = "dev"
}

variable "owner" {
  default = "david.sawicki@duolingo.com"
}

variable "ecs_cluster" {
  default = "dev"
}

variable "office_cidr_blocks" {
  type        = list(string)
  description = "List of CIDR blocks for office addresses/subnets"
  default     = ["10.1.0.0/16", "10.10.0.0/24", "10.11.0.0/24", "10.12.0.0/24", "10.30.0.0/16"]
}

variable "github_repository" {
  default = "duolingo-jeeves"
}

variable "pagerduty_rotation" {
  default = "none"
}

variable "team" {
  default = "observability-team@duolingo.com"
}
