***REMOVED*** ============================================================================
***REMOVED*** Metastore Outputs
***REMOVED*** ============================================================================

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

***REMOVED*** ============================================================================
***REMOVED*** Catalog Outputs
***REMOVED*** ============================================================================

output "workspace_catalog_name" {
  description = "Workspace catalog name (if created)"
  value       = var.create_workspace_catalog ? databricks_catalog.workspace_catalog[0].name : null
}

output "workspace_catalog_storage_root" {
  description = "Workspace catalog storage root (if created)"
  value       = var.create_workspace_catalog ? databricks_catalog.workspace_catalog[0].storage_root : null
}

***REMOVED*** ============================================================================
***REMOVED*** Storage Credential Outputs
***REMOVED*** ============================================================================

output "root_storage_credential_name" {
  description = "UC root storage credential name (null if using existing metastore)"
  value       = !local.use_existing_metastore && var.create_workspace_catalog ? databricks_storage_credential.root_storage[0].name : null
}

output "external_storage_credential_name" {
  description = "External storage credential name (if created)"
  value       = var.create_workspace_catalog ? databricks_storage_credential.external_storage[0].name : null
}

***REMOVED*** ============================================================================
***REMOVED*** External Location Outputs
***REMOVED*** ============================================================================

output "root_storage_location_url" {
  description = "UC root storage location URL (null if using existing metastore)"
  value       = !local.use_existing_metastore && var.create_workspace_catalog ? databricks_external_location.root_storage[0].url : null
}

output "external_location_url" {
  description = "External location URL (if created)"
  value       = var.create_workspace_catalog ? databricks_external_location.external_location[0].url : null
}

***REMOVED*** ============================================================================
***REMOVED*** IAM Role Outputs
***REMOVED*** ============================================================================

output "root_storage_iam_role_arn" {
  description = "UC root storage IAM role ARN (null if using existing metastore)"
  value       = !local.use_existing_metastore && var.create_workspace_catalog ? aws_iam_role.unity_catalog_root[0].arn : null
}

output "external_storage_iam_role_arn" {
  description = "UC external storage IAM role ARN (if created)"
  value       = var.create_workspace_catalog ? aws_iam_role.unity_catalog_external[0].arn : null
}

***REMOVED*** ============================================================================
***REMOVED*** Workspace Admin Outputs (DISABLED)
***REMOVED*** ============================================================================

***REMOVED*** output "workspace_admin_user_id" {
***REMOVED***   description = "Workspace admin user ID (if assigned)"
***REMOVED***   value       = var.workspace_admin_email != "" && length(data.databricks_user.workspace_admin) > 0 ? data.databricks_user.workspace_admin[0].id : null
***REMOVED*** }
***REMOVED*** 
***REMOVED*** output "workspace_admin_assignment_id" {
***REMOVED***   description = "Workspace admin permission assignment ID (if assigned)"
***REMOVED***   value       = var.workspace_admin_email != "" && length(databricks_mws_permission_assignment.workspace_admin) > 0 ? databricks_mws_permission_assignment.workspace_admin[0].id : null
***REMOVED*** }


