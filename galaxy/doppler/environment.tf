module "duolingo-jeeves-dev" {
  source  = "app.terraform.io/duolingo/galaxy/terraform//modules/doppler_environment"
  version = "~> 3.0"
  name    = "dev"
  project = "duolingo-jeeves"

  configs = [{
    name = "duolingo-jeeves"
    sync_aws_secrets_manager = {
      account     = "duolingo-main"
      environment = "dev"
      product     = "duolingo"
      regions     = ["us-east-1"]
      service     = "jeeves"
      tags = {
        github-repo = "duolingo-jeeves"
        pd-rotation = "none"
        team        = "observability-team@duolingo.com"
      }
    }
  }]
}

module "duolingo-jeeves-prod" {
  source  = "app.terraform.io/duolingo/galaxy/terraform//modules/doppler_environment"
  version = "~> 3.0"
  name    = "prod"
  project = "duolingo-jeeves"

  configs = [{
    name = "duolingo-jeeves"
    sync_aws_secrets_manager = {
      account     = "duolingo-main"
      environment = "prod"
      product     = "duolingo"
      regions     = ["us-east-1"]
      service     = "jeeves"
      tags = {
        github-repo = "duolingo-jeeves"
        pd-rotation = "grizzly"
        team        = "observability-team@duolingo.com"
      }
    }
  }]
}
