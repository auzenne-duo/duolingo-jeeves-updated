resource "aws_s3_bucket" "duolingo-jeeves" {
  bucket = "duolingo-jeeves"

  tags = {
    product     = var.product
    service     = var.service
    environment = var.environment
    owner       = var.owner
  }
}

resource "aws_s3_bucket" "jeeves-document-cache" {
  bucket = "jeeves-document-cache"

  tags = {
    product     = var.product
    service     = var.service
    environment = var.environment
    owner       = var.owner
  }
}
