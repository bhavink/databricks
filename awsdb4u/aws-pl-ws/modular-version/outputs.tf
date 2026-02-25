# ============================================================================
# Networking Outputs
# ============================================================================

output "vpc_id" {
  description = "VPC ID"
  value       = module.networking.vpc_id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = module.networking.private_subnet_ids
}

output "workspace_security_group_id" {
  description = "Workspace security group ID"
  value       = module.networking.workspace_security_group_id
}

# ============================================================================
# Storage Outputs
# ============================================================================

output "root_storage_bucket" {
  description = "Root storage bucket name"
  value       = module.storage.root_storage_bucket
}

output "unity_catalog_bucket" {
  description = "Unity Catalog metastore bucket name"
  value       = module.storage.unity_catalog_bucket
}

output "unity_catalog_external_bucket" {
  description = "Unity Catalog external location bucket name"
  value       = module.storage.unity_catalog_external_bucket
}

output "unity_catalog_root_storage_bucket" {
  description = "Unity Catalog root storage bucket name"
  value       = module.storage.unity_catalog_root_storage_bucket
}

# ============================================================================
# IAM Outputs
# ============================================================================

output "cross_account_role_arn" {
  description = "Cross-account IAM role ARN"
  value       = module.iam.cross_account_role_arn
}

output "instance_profile_arn" {
  description = "Instance profile ARN"
  value       = module.iam.instance_profile_arn
}

# ============================================================================
# Workspace Outputs
# ============================================================================

output "workspace_id" {
  description = "Databricks workspace ID"
  value       = module.databricks_workspace.workspace_id
}

output "workspace_url" {
  description = "Databricks workspace URL"
  value       = module.databricks_workspace.workspace_url
}

output "workspace_status" {
  description = "Databricks workspace status"
  value       = module.databricks_workspace.workspace_status
}

# ============================================================================
# Unity Catalog Outputs
# ============================================================================

output "metastore_id" {
  description = "Unity Catalog metastore ID"
  value       = module.unity_catalog.metastore_id
}

output "workspace_catalog_name" {
  description = "Workspace catalog name"
  value       = module.unity_catalog.workspace_catalog_name
}

output "root_storage_location_url" {
  description = "UC root storage location URL"
  value       = module.unity_catalog.root_storage_location_url
}

output "external_location_url" {
  description = "UC external location URL"
  value       = module.unity_catalog.external_location_url
}

# ============================================================================
# User Assignment Outputs
# ============================================================================

output "workspace_admin_user_id" {
  description = "Workspace admin user ID (if assigned)"
  value       = length(module.user_assignment) > 0 ? module.user_assignment[0].user_id : null
}

output "workspace_admin_user_name" {
  description = "Workspace admin email address"
  value       = length(module.user_assignment) > 0 ? module.user_assignment[0].user_name : null
}

output "workspace_admin_permission_id" {
  description = "Workspace admin permission assignment ID"
  value       = length(module.user_assignment) > 0 ? module.user_assignment[0].permission_assignment_id : null
}

# ============================================================================
# Deployment Summary
# ============================================================================

output "deployment_summary" {
  description = "Deployment summary and next steps"
  value       = <<-EOT
    
    ==========================================
    Databricks Private Link Deployment Complete
    ==========================================
    
    Workspace Details:
    - Name: ${local.workspace_name}
    - URL: ${module.databricks_workspace.workspace_url}
    - Region: ${var.region}
    - Status: ${module.databricks_workspace.workspace_status}
    
    Unity Catalog:
    - Metastore ID: ${module.unity_catalog.metastore_id}
    - Workspace Catalog: ${module.unity_catalog.workspace_catalog_name}
    - Root Storage: ${module.unity_catalog.root_storage_location_url}
    - External Location: ${module.unity_catalog.external_location_url}
    
    Workspace Administrator:
    - Email: ${var.workspace_admin_email}
    - Catalog Privileges: ALL_PRIVILEGES
    
    ⏰ IMPORTANT: Wait 20 minutes before creating clusters!
    
    Next Steps:
    1. Wait 20 minutes for backend private link to stabilize
    2. Access workspace at: ${module.databricks_workspace.workspace_url}
    3. Log in with: ${var.workspace_admin_email}
    4. Verify catalog: ${module.unity_catalog.workspace_catalog_name}
    
    ==========================================
  EOT
}

