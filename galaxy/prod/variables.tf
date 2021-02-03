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
  default = "Peter Pearson"
}

variable "ecs_cluster" {
  default = "prod"
}
