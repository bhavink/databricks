# ============================================================================
# S3 Encryption KMS Key Outputs
# ============================================================================

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

# ============================================================================
# Workspace CMK Outputs
# ============================================================================

output "workspace_storage_key_arn" {
  description = "Workspace KMS key ARN (for DBFS, EBS, and managed services encryption)"
  value       = var.enable_workspace_cmk ? aws_kms_key.workspace_storage[0].arn : null
}

output "workspace_storage_key_id" {
  description = "Workspace KMS key ID"
  value       = var.enable_workspace_cmk ? aws_kms_key.workspace_storage[0].key_id : null
}

output "workspace_storage_key_alias" {
  description = "Workspace KMS key alias"
  value       = var.enable_workspace_cmk ? aws_kms_alias.workspace_storage[0].name : null
}

