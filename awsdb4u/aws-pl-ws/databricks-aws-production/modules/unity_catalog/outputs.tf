# ============================================================================
# Metastore Outputs
# ============================================================================

output "metastore_id" {
  description = "Unity Catalog metastore ID (existing or created by Terraform)"
  value       = local.effective_metastore_id
}

output "metastore_name" {
  description = "Unity Catalog metastore name (null if using existing metastore)"
  value       = local.use_existing_metastore ? null : databricks_metastore.this[0].name
}

output "metastore_region" {
  description = "Unity Catalog metastore region (null if using existing metastore)"
  value       = local.use_existing_metastore ? null : databricks_metastore.this[0].region
}

output "metastore_assignment_id" {
  description = "Metastore assignment ID for this workspace"
  value       = databricks_metastore_assignment.workspace_assignment.id
}

# ============================================================================
# Catalog Outputs
# ============================================================================

output "workspace_catalog_name" {
  description = "Workspace catalog name (if created)"
  value       = var.create_workspace_catalog ? databricks_catalog.workspace_catalog[0].name : null
}

output "workspace_catalog_storage_root" {
  description = "Workspace catalog storage root (if created)"
  value       = var.create_workspace_catalog ? databricks_catalog.workspace_catalog[0].storage_root : null
}

# ============================================================================
# Storage Credential Outputs
# ============================================================================

output "root_storage_credential_name" {
  description = "UC root storage credential name (null if using existing metastore)"
  value       = !local.use_existing_metastore && var.create_workspace_catalog ? databricks_storage_credential.root_storage[0].name : null
}

output "external_storage_credential_name" {
  description = "External storage credential name (if created)"
  value       = var.create_workspace_catalog ? databricks_storage_credential.external_storage[0].name : null
}

# ============================================================================
# External Location Outputs
# ============================================================================

output "root_storage_location_url" {
  description = "UC root storage location URL (null if using existing metastore)"
  value       = !local.use_existing_metastore && var.create_workspace_catalog ? databricks_external_location.root_storage[0].url : null
}

output "external_location_url" {
  description = "External location URL (if created)"
  value       = var.create_workspace_catalog ? databricks_external_location.external_location[0].url : null
}

# ============================================================================
# IAM Role Outputs
# ============================================================================

output "root_storage_iam_role_arn" {
  description = "UC root storage IAM role ARN (null if using existing metastore)"
  value       = !local.use_existing_metastore && var.create_workspace_catalog ? aws_iam_role.unity_catalog_root[0].arn : null
}

output "external_storage_iam_role_arn" {
  description = "UC external storage IAM role ARN (if created)"
  value       = var.create_workspace_catalog ? aws_iam_role.unity_catalog_external[0].arn : null
}

# ============================================================================
# Workspace Admin Outputs (DISABLED)
# ============================================================================

# output "workspace_admin_user_id" {
#   description = "Workspace admin user ID (if assigned)"
#   value       = var.workspace_admin_email != "" && length(data.databricks_user.workspace_admin) > 0 ? data.databricks_user.workspace_admin[0].id : null
# }
# 
# output "workspace_admin_assignment_id" {
#   description = "Workspace admin permission assignment ID (if assigned)"
#   value       = var.workspace_admin_email != "" && length(databricks_mws_permission_assignment.workspace_admin) > 0 ? databricks_mws_permission_assignment.workspace_admin[0].id : null
# }


