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
  default = "Peter Chapman"
}

variable "ecs_cluster" {
  default = "dev"
}
