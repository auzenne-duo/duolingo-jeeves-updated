provider "aws" {
  region = "us-east-1"
}

terraform {
  backend "s3" {
    bucket         = "infra-galaxy-state"
    key            = "duolingo/duolingo-jeeves/doppler/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = "true"
    dynamodb_table = "infra-galaxy-lock"
  }

  required_version = "1.5.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    doppler = {
      source  = "DopplerHQ/doppler"
      version = "~> 1.12"
    }
  }
}
