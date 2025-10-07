// KBD-IR specific infrastructure (S3 bucket + SES identity)

resource "aws_s3_bucket" "kbdir_prod" {
  bucket = var.kbdir_bucket_name

  tags = {
    Service     = "kbd-ir"
    Environment = "prod"
  }
}

resource "aws_s3_bucket_versioning" "kbdir_prod" {
  bucket = aws_s3_bucket.kbdir_prod.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "kbdir_prod" {
  bucket = aws_s3_bucket.kbdir_prod.bucket

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_ses_domain_identity" "kbdir" {
  domain = var.kbdir_domain
}

resource "aws_ses_domain_dkim" "kbdir" {
  domain = aws_ses_domain_identity.kbdir.domain
}
