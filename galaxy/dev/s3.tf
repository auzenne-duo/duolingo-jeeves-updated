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

resource "aws_s3_bucket_lifecycle_configuration" "jeeves-document-cache-dev-cleanup" {
  bucket = aws_s3_bucket.jeeves-document-cache-dev.id
  rule {
    id = "jeeves-document-cache-dev-cleanup-app-figures"
    filter {
      prefix = "AppFigures/"
    }
    status = "Enabled"
    expiration {
      days = 365
    }
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
  rule {
    id = "jeeves-document-cache-dev-cleanup-zendesk"
    filter {
      prefix = "Zendesk/"
    }
    status = "Enabled"
    expiration {
      days = 365
    }
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
  rule {
    id = "jeeves-document-cache-dev-cleanup-jira"
    filter {
      prefix = "JIRA/"
    }
    status = "Enabled"
    expiration {
      days = 365
    }
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
  rule {
    id = "jeeves-document-cache-dev-cleanup-reddit"
    filter {
      prefix = "Reddit/"
    }
    status = "Enabled"
    expiration {
      days = 365
    }
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}
