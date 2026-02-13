# ==============================================
# Primary Outputs (Most Commonly Used)
# ==============================================

output "workspace_url" {
  description = "Databricks workspace URL"
  value       = module.workspace.workspace_url
}

output "workspace_id" {
  description = "Azure resource ID of the workspace"
  value       = module.workspace.workspace_id
}

output "metastore_id" {
  description = "Unity Catalog metastore ID"
  value       = module.unity_catalog.metastore_id
}

output "nat_gateway_ip" {
  description = "Public IP for NAT Gateway (for firewall allowlisting)"
  value       = module.networking.nat_gateway_public_ip
}

# ==============================================
# Detailed Resource Outputs (Hidden by Default)
# ==============================================

output "resources" {
  description = "Detailed resource information (workspace, network, Unity Catalog, NCC, SEP)"
  value = {
    workspace = {
      name   = module.workspace.workspace_name
      url    = module.workspace.workspace_url
      id     = module.workspace.workspace_id
      region = var.location
    }
    network = {
      vnet_id    = module.networking.vnet_id
      vnet_name  = module.networking.vnet_name
      subnet_ids = module.networking.subnet_ids
      nat_ip     = module.networking.nat_gateway_public_ip
    }
    unity_catalog = {
      metastore_id       = module.unity_catalog.metastore_id
      metastore_name     = module.unity_catalog.metastore_name
      external_location  = module.unity_catalog.external_location_name
      external_storage   = module.unity_catalog.external_storage_account_name
    }
    ncc = {
      id   = module.ncc.ncc_id
      name = module.ncc.ncc_name
    }
    service_endpoint_policy = var.enable_service_endpoint_policy ? {
      id                  = module.service_endpoint_policy[0].service_endpoint_policy_id
      name                = module.service_endpoint_policy[0].service_endpoint_policy_name
      allowed_storage_ids = module.service_endpoint_policy[0].allowed_storage_accounts
    } : null
    customer_managed_keys = local.cmk_enabled ? {
      key_vault_id          = local.create_key_vault ? module.key_vault[0].key_vault_id : var.existing_key_vault_id
      key_vault_name        = local.create_key_vault ? module.key_vault[0].key_vault_name : "existing"
      key_id                = local.create_key_vault ? module.key_vault[0].key_id : var.existing_key_id
      managed_services      = var.enable_cmk_managed_services
      managed_disks         = var.enable_cmk_managed_disks
      dbfs_root             = var.enable_cmk_dbfs_root
      auto_rotation_enabled = local.create_key_vault ? true : null
      disk_encryption_set   = var.enable_cmk_managed_disks ? {
        resource_id  = module.workspace.disk_encryption_set_identity.resource_id
        principal_id = module.workspace.disk_encryption_set_identity.principal_id
      } : null
    } : null
  }
}

# ==============================================
# Deployment Summary
# ==============================================

output "deployment_summary" {
  description = "Quick status overview of deployed resources"
  value = <<-EOT
  
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ Databricks Non-PL Workspace Deployed
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  
  🌐 Workspace URL:  ${module.workspace.workspace_url}
  📍 Region:         ${var.location}
  🔒 Pattern:        Non-PL (NPIP enabled workspace)
  
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🛡️  Security & Connectivity Status
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  
  ✅ Secure Cluster Connectivity (NPIP)
  ✅ Unity Catalog: ${module.unity_catalog.metastore_id}
  ✅ NCC (Serverless-Ready): ${module.ncc.ncc_id}
  ${var.enable_service_endpoint_policy ? "✅ Service Endpoint Policy: Enabled" : "⚠️  Service Endpoint Policy: Disabled"}
  ${local.enable_nat_gateway ? "✅ NAT Gateway: ${module.networking.nat_gateway_public_ip}" : "⚠️  NAT Gateway: Disabled (using BYOR)"}
  ${local.cmk_enabled ? "✅ Customer-Managed Keys: Enabled (${var.enable_cmk_managed_services ? "Managed Services" : ""}${var.enable_cmk_managed_services && var.enable_cmk_managed_disks ? " + " : ""}${var.enable_cmk_managed_disks ? "Managed Disks" : ""}${(var.enable_cmk_managed_services || var.enable_cmk_managed_disks) && var.enable_cmk_dbfs_root ? " + " : ""}${var.enable_cmk_dbfs_root ? "DBFS Root" : ""})" : "⚠️  Customer-Managed Keys: Disabled"}
  ${var.enable_cmk_managed_services || var.enable_cmk_managed_disks ? "✅ Customer-Managed Keys: Enabled" : "⚠️  Customer-Managed Keys: Disabled (optional)"}
  ${var.enable_ip_access_lists ? "✅ IP Access Lists: Enabled" : "⚠️  IP Access Lists: Disabled (optional)"}
  
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📚 Next Steps
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  
  1. Access workspace → ${module.workspace.workspace_url}
  2. Configure Unity Catalog (catalogs, schemas)
  3. Set up users, groups, and permissions
  4. Create compute policies and clusters
  5. (Optional) Enable serverless → See docs/SERVERLESS-SETUP.md
  
  💡 For detailed resource IDs, run: terraform output resources
  
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  
  EOT
}
