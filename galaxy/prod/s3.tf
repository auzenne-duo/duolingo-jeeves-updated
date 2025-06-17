resource "aws_s3_bucket" "duolingo-jeeves" {
  bucket = "duolingo-jeeves"

  tags = {
    product     = var.product
    service     = var.service
    environment = var.environment
  }
}

resource "aws_s3_bucket_public_access_block" "duolingo-jeeves" {
  bucket = aws_s3_bucket.duolingo-jeeves.id

  block_public_acls  = true
  ignore_public_acls = true

  block_public_policy = true
}

resource "aws_s3_bucket" "jeeves-document-cache" {
  bucket = "jeeves-document-cache"

  tags = {
    product     = var.product
    service     = var.service
    environment = var.environment
  }
}

resource "aws_s3_bucket_public_access_block" "jeeves-document-cache" {
  bucket = aws_s3_bucket.jeeves-document-cache.id

  block_public_acls  = true
  ignore_public_acls = true

  block_public_policy = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "duolingo-jeeves" {
  bucket = aws_s3_bucket.duolingo-jeeves.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "jeeves-document-cache" {
  bucket = aws_s3_bucket.jeeves-document-cache.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
