resource "aws_s3_bucket" "jeeves-document-cache-dev" {
  bucket = "jeeves-document-cache-dev"

  tags = {
    product     = var.product
    service     = var.service
    environment = var.environment
    owner       = var.owner
  }

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
}

resource "aws_s3_bucket_public_access_block" "jeeves-document-cache-dev" {
  bucket = aws_s3_bucket.jeeves-document-cache-dev.id

  block_public_acls  = true
  ignore_public_acls = true

  block_public_policy = true
}
