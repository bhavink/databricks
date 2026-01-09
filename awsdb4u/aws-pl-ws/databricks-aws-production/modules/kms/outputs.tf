***REMOVED*** ============================================================================
***REMOVED*** S3 Encryption KMS Key Outputs
***REMOVED*** ============================================================================

output "key_id" {
  description = "S3 KMS key ID (if encryption enabled)"
  value       = var.enable_encryption ? aws_kms_key.databricks[0].key_id : null
}

output "key_arn" {
  description = "S3 KMS key ARN (if encryption enabled)"
  value       = var.enable_encryption ? aws_kms_key.databricks[0].arn : null
}

output "key_alias" {
  description = "S3 KMS key alias (if encryption enabled)"
  value       = var.enable_encryption ? aws_kms_alias.databricks[0].name : null
}

***REMOVED*** ============================================================================
***REMOVED*** Workspace CMK Outputs
***REMOVED*** ============================================================================

output "workspace_storage_key_arn" {
  description = "Workspace KMS key ARN (for DBFS, EBS, and managed services encryption)"
  value       = var.enable_workspace_cmk ? (local.use_existing_key ? var.existing_workspace_cmk_key_arn : aws_kms_key.workspace_storage[0].arn) : null
}

output "workspace_storage_key_id" {
  description = "Workspace KMS key ID"
  value       = var.enable_workspace_cmk ? (local.use_existing_key ? null : aws_kms_key.workspace_storage[0].key_id) : null
}

output "workspace_storage_key_alias" {
  description = "Workspace KMS key alias"
  value       = var.enable_workspace_cmk ? (local.use_existing_key ? var.existing_workspace_cmk_key_alias : aws_kms_alias.workspace_storage[0].name) : null
}

