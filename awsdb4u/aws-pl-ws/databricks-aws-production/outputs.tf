# ============================================================================
# Networking Outputs
# ============================================================================

output "vpc_id" {
  description = "VPC ID"
  value       = module.networking.vpc_id
}

output "availability_zones" {
  description = "Availability zones used for deployment (auto-detected or manually specified)"
  value       = local.availability_zones
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
  description = "Workspace DBFS/Root storage bucket name"
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


output "private_access_settings_id" {
  description = <<-EOT
    Private Access Settings ID (existing or newly created).
    Use this value for 'existing_private_access_settings_id' when deploying additional workspaces
    that should share the same frontend Private Link configuration (same transit VPC).
  EOT
  value       = module.databricks_workspace.private_access_settings_id
}

output "private_access_settings_created" {
  description = "Whether a new Private Access Settings was created (false if reusing existing PAS)"
  value       = module.databricks_workspace.private_access_settings_created
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

    Network Configuration:
    - VPC CIDR: ${var.vpc_cidr}
    - Availability Zones: ${join(", ", local.availability_zones)}
    - Private Link: ${var.enable_private_link ? "Enabled (Full Private Link - Workspace + Relay VPCEs)" : "Disabled (Public Internet via NAT Gateway)"}
    - AWS Service Endpoints: Always enabled (S3/STS/Kinesis)

    Encryption (Customer Managed Keys):
    - CMK Enabled: ${var.enable_encryption || var.enable_workspace_cmk ? "Yes" : "No"}
    - S3 Bucket Encryption: ${var.enable_encryption ? "Enabled (KMS)" : "Disabled (AWS-managed)"}
    - Workspace CMK (DBFS/EBS/Managed Services): ${var.enable_workspace_cmk ? (var.existing_workspace_cmk_key_arn != "" ? "Enabled (Existing Key)" : "Enabled (New Key)") : "Disabled"}
    - KMS Key ARN (S3): ${var.enable_encryption ? module.kms.key_arn : "N/A"}
    - Workspace Storage Key ARN: ${var.enable_workspace_cmk ? module.kms.workspace_storage_key_arn : "N/A"}

    Unity Catalog:
    - Metastore ID: ${module.unity_catalog.metastore_id}
    - Metastore Source: ${var.metastore_id != "" ? "Existing" : "New"}
    - Workspace Catalog: ${coalesce(module.unity_catalog.workspace_catalog_name, "N/A")}
    - Unity Catalog Root Storage: ${coalesce(module.unity_catalog.root_storage_location_url, "N/A (using existing metastore)")}
    - Workspace Catalog Storage Location: ${coalesce(module.unity_catalog.external_location_url, "N/A")}

    Workspace Administrator:
    - Email: ${var.workspace_admin_email}
    - Catalog Privileges: ALL_PRIVILEGES

    ⏰ IMPORTANT: Wait 20 minutes before creating clusters!

    Next Steps:
    1. Wait 20 minutes for backend private link to stabilize
    2. Access workspace at: ${module.databricks_workspace.workspace_url}
    3. Log in with: ${var.workspace_admin_email}
    4. Verify catalog: ${coalesce(module.unity_catalog.workspace_catalog_name, "N/A")}

    ==========================================
  EOT
}

