# ==============================================
# Primary Outputs (Most Commonly Used)
# ==============================================

output "workspace_url" {
  description = "Databricks workspace URL (accessible via Private Link only)"
  value       = module.workspace.workspace_url
}

output "workspace_id" {
  description = "Azure resource ID of the workspace"
  value       = module.workspace.workspace_id
}

output "metastore_id" {
  description = "Unity Catalog metastore ID"
  value       = var.create_metastore ? module.unity_catalog.metastore_id : var.existing_metastore_id
}

# ==============================================
# Detailed Resource Outputs (Hidden by Default)
# ==============================================

output "resources" {
  description = "Detailed resource information (workspace, network, Unity Catalog, Private Endpoints, NCC, SEP)"
  value = {
    workspace = {
      name         = module.workspace.workspace_name
      url          = module.workspace.workspace_url
      id           = module.workspace.workspace_id
      id_numeric   = module.workspace.workspace_id_numeric
      region       = var.location
    }
    network = {
      vnet_id      = module.networking.vnet_id
      vnet_name    = module.networking.vnet_name
      subnet_ids   = module.networking.subnet_ids
      subnet_names = module.networking.subnet_names
      nsg_id       = module.networking.nsg_id
    }
    unity_catalog = {
      metastore_id         = var.create_metastore ? module.unity_catalog.metastore_id : var.existing_metastore_id
      metastore_storage    = var.create_metastore ? module.unity_catalog.metastore_storage_account_name : "N/A (using existing)"
      external_location    = module.unity_catalog.external_location_url
      external_storage     = module.unity_catalog.external_storage_account_name
    }
    private_endpoints = {
      ui_api_endpoint_id          = module.private_endpoints.databricks_ui_api_private_endpoint_id
      browser_auth_endpoint_id    = module.private_endpoints.browser_authentication_private_endpoint_id
      private_dns_zones           = module.private_endpoints.private_dns_zones
      summary                     = module.private_endpoints.private_endpoints_summary
    }
    ncc = var.enable_ncc ? {
      id   = module.ncc[0].ncc_id
      name = module.ncc[0].ncc_name
    } : null
    service_endpoint_policy = var.enable_service_endpoint_policy ? {
      id                  = module.service_endpoint_policy[0].service_endpoint_policy_id
      name                = module.service_endpoint_policy[0].service_endpoint_policy_name
      allowed_storage_ids = module.service_endpoint_policy[0].allowed_storage_accounts
    } : null
    customer_managed_keys = (var.enable_cmk_managed_services || var.enable_cmk_managed_disks || var.enable_cmk_dbfs_root) ? {
      key_vault_id     = var.cmk_key_vault_id
      key_id           = var.cmk_key_vault_key_id
      managed_services = var.enable_cmk_managed_services
      managed_disks    = var.enable_cmk_managed_disks
      dbfs_root        = var.enable_cmk_dbfs_root
      disk_encryption_set = var.enable_cmk_managed_disks ? {
        resource_id  = module.workspace.disk_encryption_set_identity.resource_id
        principal_id = module.workspace.disk_encryption_set_identity.principal_id
      } : null
    } : null
    resource_group = {
      name = local.resource_group_name
      id   = var.use_byor_infrastructure ? null : azurerm_resource_group.this[0].id
    }
  }
}

# ==============================================
# Deployment Summary
# ==============================================

output "deployment_summary" {
  description = "Quick status overview of deployed resources"
  value = <<-EOT
  
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ Databricks Full Private Workspace Deployed
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  
  🌐 Workspace URL:  ${module.workspace.workspace_url}
  📍 Region:         ${var.location}
  🔒 Pattern:        Full Private (NPIP enabled workspace)
  
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🛡️  Security & Connectivity Status
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  
  ✅ Secure Cluster Connectivity (NPIP)
  ✅ Private Link: Control Plane + Data Plane
  ✅ Unity Catalog: ${var.create_metastore ? module.unity_catalog.metastore_id : var.existing_metastore_id}
  ${var.enable_ncc ? "✅ NCC (Serverless-Ready): ${module.ncc[0].ncc_id}" : "⚠️  NCC: Disabled (enable for serverless compute)"}
  ${var.enable_service_endpoint_policy ? "✅ Service Endpoint Policy: Enabled" : "⚠️  Service Endpoint Policy: Disabled (optional)"}
  ${var.enable_cmk_managed_services || var.enable_cmk_managed_disks || var.enable_cmk_dbfs_root ? "✅ Customer-Managed Keys: Enabled" : "⚠️  Customer-Managed Keys: Disabled (optional)"}
  ${var.enable_ip_access_lists ? "✅ IP Access Lists: Enabled" : "⚠️  IP Access Lists: Disabled (optional)"}
  ${var.enable_public_network_access ? "🔓 Public Access: Enabled (lock down after deployment)" : "🔒 Public Access: Disabled (Private Link only)"}
  
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📚 Next Steps
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  
  1. Access workspace → ${module.workspace.workspace_url}
     ${var.enable_public_network_access ? "⚠️  Lock down: Set enable_public_network_access=false and re-apply" : "✅ Requires VPN/Bastion/Jump Box for access"}
  2. Configure Unity Catalog (catalogs, schemas)
  3. Set up users, groups, and permissions
  4. Create compute policies and clusters
  5. (Optional) Enable serverless → See docs/04-SERVERLESS-SETUP.md
  
  💡 For detailed resource IDs, run: terraform output resources
  
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  
  EOT
}
