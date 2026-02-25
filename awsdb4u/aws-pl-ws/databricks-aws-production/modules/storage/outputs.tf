# ============================================================================
# S3 Bucket Outputs
# ============================================================================

output "root_storage_bucket" {
  description = "Root storage bucket name"
  value       = aws_s3_bucket.root_storage.bucket
}

output "root_storage_bucket_arn" {
  description = "Root storage bucket ARN"
  value       = aws_s3_bucket.root_storage.arn
}

output "unity_catalog_bucket" {
  description = "Unity Catalog metastore bucket name"
  value       = aws_s3_bucket.unity_catalog.bucket
}

output "unity_catalog_bucket_arn" {
  description = "Unity Catalog metastore bucket ARN"
  value       = aws_s3_bucket.unity_catalog.arn
}

output "unity_catalog_external_bucket" {
  description = "Unity Catalog external location bucket name"
  value       = aws_s3_bucket.unity_catalog_external.bucket
}

output "unity_catalog_external_bucket_arn" {
  description = "Unity Catalog external location bucket ARN"
  value       = aws_s3_bucket.unity_catalog_external.arn
}

output "unity_catalog_root_storage_bucket" {
  description = "Unity Catalog root storage bucket name (null if not created)"
  value       = var.create_uc_root_storage_bucket ? aws_s3_bucket.unity_catalog_root_storage[0].bucket : null
}

output "unity_catalog_root_storage_bucket_arn" {
  description = "Unity Catalog root storage bucket ARN (null if not created)"
  value       = var.create_uc_root_storage_bucket ? aws_s3_bucket.unity_catalog_root_storage[0].arn : null
}

