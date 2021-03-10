resource "aws_s3_bucket" "jeeves-document-cache-dev" {
  bucket = "jeeves-document-cache-dev"

  tags = {
    product     = var.product
    service     = var.service
    environment = var.environment
    owner       = var.owner
  }
}
