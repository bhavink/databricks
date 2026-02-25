# ============================================================================
# Storage Module - Provider Configuration
# ============================================================================

terraform {
  required_providers {
    databricks = {
      source                = "databricks/databricks"
      version               = "~> 1.0"
      configuration_aliases = [databricks.account]
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ============================================================================
# S3 Bucket - Databricks Root Storage (DBFS)
# ============================================================================

resource "aws_s3_bucket" "root_storage" {
  bucket        = "${var.root_storage_bucket_name}-${var.suffix}"
  force_destroy = true

  tags = merge(var.tags, {
    Name = "${var.prefix}-root-storage"
  })
}

resource "aws_s3_bucket_versioning" "root_storage" {
  bucket = aws_s3_bucket.root_storage.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "root_storage" {
  bucket = aws_s3_bucket.root_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Use Databricks-generated bucket policy data source
data "databricks_aws_bucket_policy" "root_storage" {
  provider                 = databricks.account
  databricks_e2_account_id = var.databricks_account_id
  bucket                   = aws_s3_bucket.root_storage.bucket
}

resource "aws_s3_bucket_policy" "root_storage" {
  bucket = aws_s3_bucket.root_storage.id
  policy = data.databricks_aws_bucket_policy.root_storage.json

  depends_on = [
    aws_s3_bucket_public_access_block.root_storage
  ]
}

resource "aws_s3_bucket_server_side_encryption_configuration" "root_storage" {
  bucket = aws_s3_bucket.root_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.enable_encryption ? "aws:kms" : "AES256"
      kms_master_key_id = var.enable_encryption ? var.kms_key_arn : null
    }
  }
}

# ============================================================================
# S3 Bucket - Unity Catalog Metastore
# ============================================================================

resource "aws_s3_bucket" "unity_catalog" {
  bucket        = "${var.unity_catalog_bucket_name}-${var.suffix}"
  force_destroy = true

  tags = merge(var.tags, {
    Name = "${var.prefix}-unity-catalog"
  })
}

resource "aws_s3_bucket_versioning" "unity_catalog" {
  bucket = aws_s3_bucket.unity_catalog.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "unity_catalog" {
  bucket = aws_s3_bucket.unity_catalog.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "unity_catalog" {
  bucket = aws_s3_bucket.unity_catalog.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.enable_encryption ? "aws:kms" : "AES256"
      kms_master_key_id = var.enable_encryption ? var.kms_key_arn : null
    }
  }
}

# ============================================================================
# S3 Bucket - Unity Catalog External Location
# ============================================================================

resource "aws_s3_bucket" "unity_catalog_external" {
  bucket        = "${var.unity_catalog_external_bucket_name}-${var.suffix}"
  force_destroy = true

  tags = merge(var.tags, {
    Name = "${var.prefix}-unity-catalog-external"
  })
}

resource "aws_s3_bucket_versioning" "unity_catalog_external" {
  bucket = aws_s3_bucket.unity_catalog_external.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "unity_catalog_external" {
  bucket = aws_s3_bucket.unity_catalog_external.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "unity_catalog_external" {
  bucket = aws_s3_bucket.unity_catalog_external.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.enable_encryption ? "aws:kms" : "AES256"
      kms_master_key_id = var.enable_encryption ? var.kms_key_arn : null
    }
  }
}

# ============================================================================
# S3 Bucket - Unity Catalog Root Storage
# ============================================================================

resource "aws_s3_bucket" "unity_catalog_root_storage" {
  bucket        = "${var.unity_catalog_root_storage_bucket_name}-${var.suffix}"
  force_destroy = true

  tags = merge(var.tags, {
    Name = "${var.prefix}-unity-catalog-root-storage"
  })
}

resource "aws_s3_bucket_versioning" "unity_catalog_root_storage" {
  bucket = aws_s3_bucket.unity_catalog_root_storage.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "unity_catalog_root_storage" {
  bucket = aws_s3_bucket.unity_catalog_root_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "unity_catalog_root_storage" {
  bucket = aws_s3_bucket.unity_catalog_root_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.enable_encryption ? "aws:kms" : "AES256"
      kms_master_key_id = var.enable_encryption ? var.kms_key_arn : null
    }
  }
}

