***REMOVED*** ==============================================
***REMOVED*** Workspace Outputs
***REMOVED*** ==============================================

output "workspace_url" {
  description = "Databricks workspace URL (accessible via Private Link only)"
  value       = module.workspace.workspace_url
}

output "workspace_id" {
  description = "Databricks workspace Azure resource ID"
  value       = module.workspace.workspace_id
}

output "workspace_id_numeric" {
  description = "Databricks workspace numeric ID"
  value       = module.workspace.workspace_id_numeric
}

output "workspace_name" {
  description = "Databricks workspace name"
  value       = module.workspace.workspace_name
}

***REMOVED*** ==============================================
***REMOVED*** Network Outputs
***REMOVED*** ==============================================

output "vnet_id" {
  description = "Virtual Network ID"
  value       = module.networking.vnet_id
}

output "vnet_name" {
  description = "Virtual Network name"
  value       = module.networking.vnet_name
}

output "subnet_ids" {
  description = "Subnet IDs"
  value       = module.networking.subnet_ids
}

output "subnet_names" {
  description = "Subnet names"
  value       = module.networking.subnet_names
}

output "nsg_id" {
  description = "Network Security Group ID"
  value       = module.networking.nsg_id
}

***REMOVED*** ==============================================
***REMOVED*** Private Endpoints Outputs
***REMOVED*** ==============================================

output "private_dns_zones" {
  description = "Private DNS zone IDs"
  value       = module.private_endpoints.private_dns_zones
}

output "databricks_ui_api_private_endpoint_id" {
  description = "Databricks UI/API Private Endpoint ID"
  value       = module.private_endpoints.databricks_ui_api_private_endpoint_id
}

output "browser_authentication_private_endpoint_id" {
  description = "Browser Authentication Private Endpoint ID"
  value       = module.private_endpoints.browser_authentication_private_endpoint_id
}

***REMOVED*** ==============================================
***REMOVED*** Unity Catalog Outputs
***REMOVED*** ==============================================

output "metastore_id" {
  description = "Unity Catalog metastore ID"
  value       = var.create_metastore ? module.unity_catalog.metastore_id : var.existing_metastore_id
}

output "metastore_storage_account_name" {
  description = "Unity Catalog metastore storage account name"
  value       = var.create_metastore ? module.unity_catalog.metastore_storage_account_name : "N/A (using existing)"
}

output "external_location_storage_account_name" {
  description = "Unity Catalog external location storage account name"
  value       = module.unity_catalog.external_storage_account_name
}

output "external_location_url" {
  description = "Unity Catalog external location URL"
  value       = module.unity_catalog.external_location_url
}

***REMOVED*** ==============================================
***REMOVED*** NCC Outputs
***REMOVED*** ==============================================

output "ncc_id" {
  description = "Network Connectivity Configuration ID (null if NCC not enabled)"
  value       = var.enable_ncc ? module.ncc[0].ncc_id : null
}

output "ncc_name" {
  description = "Network Connectivity Configuration Name (null if NCC not enabled)"
  value       = var.enable_ncc ? module.ncc[0].ncc_name : null
}

***REMOVED*** ==============================================
***REMOVED*** Resource Group Outputs
***REMOVED*** ==============================================

output "resource_group_name" {
  description = "Resource group name"
  value       = azurerm_resource_group.this.name
}

output "resource_group_id" {
  description = "Resource group ID"
  value       = azurerm_resource_group.this.id
}

output "location" {
  description = "Azure region"
  value       = var.location
}

***REMOVED*** ==============================================
***REMOVED*** Deployment Summary
***REMOVED*** ==============================================

output "deployment_summary" {
  description = "Summary of Full Private deployment configuration"
  value = {
    pattern                   = "full-private"
    deployment_type           = "Full Private Link (Air-Gapped)"
    control_plane_access      = "Private Link only"
    data_plane_access         = "Private (NPIP - no public IPs)"
    egress_method             = "None (air-gapped - no internet)"
    storage_connectivity      = "Private Link (all storage)"
    unity_catalog             = "Enabled (private storage)"
    nat_gateway_enabled       = false
    private_link_enabled      = true
    cmk_managed_services      = var.enable_cmk_managed_services
    cmk_managed_disks         = var.enable_cmk_managed_disks
    cmk_dbfs_root             = var.enable_cmk_dbfs_root
    ip_access_lists_enabled   = var.enable_ip_access_lists
    private_endpoints_count   = module.private_endpoints.private_endpoints_summary.total_private_endpoints
    ncc_enabled               = var.enable_ncc
    workspace_url             = module.workspace.workspace_url
    metastore_created         = var.create_metastore
    access_connector_created  = var.create_access_connector
    random_suffix             = random_string.deployment_suffix.result
  }
}

***REMOVED*** ==============================================
***REMOVED*** Next Steps
***REMOVED*** ==============================================

output "next_steps" {
  description = "Recommended next steps after deployment"
  value = <<-EOT
    
    ✅ Full Private Azure Databricks Workspace Deployed Successfully!
    
    📋 Next Steps:
    
    1. NETWORK ACCESS STATUS:
       ${var.enable_public_network_access ? "🔓 PUBLIC ACCESS ENABLED - Workspace is currently accessible from the internet." : "🔒 AIR-GAPPED - Workspace locked to Private Link only."}
       Workspace URL: ${module.workspace.workspace_url}
       ${var.enable_public_network_access ? "\n       ⚠️  RECOMMENDED: Lock down workspace after deployment:\n          - Set 'enable_public_network_access = false' in terraform.tfvars\n          - Run 'terraform apply' to enforce Private Link only\n          - Future access requires VPN/Bastion/Jump Box" : "       ✅ Access requires network connectivity to VNet (VPN/ExpressRoute/Bastion)"}
    
    2. Configure Unity Catalog:
       - Metastore: ${var.create_metastore ? "Created" : "Using existing"}
       - External Location: ${module.unity_catalog.external_location_url}
    
    3. Important Notes for Air-Gapped Deployment:
       - ❌ No internet egress (NAT Gateway not configured)
       - ❌ Cannot download packages from PyPI, Maven, Docker Hub directly
       - ✅ Use custom package repositories within your network
       - ✅ Pre-install libraries via init scripts from internal storage
    
    4. Security Features Enabled:
       - ✅ Private Link for control plane
       - ✅ Secure Cluster Connectivity (NPIP)
       - ✅ Private Endpoints for all storage
       ${var.enable_ncc ? "- ✅ Network Connectivity Configuration (NCC) for Serverless" : "- ⏸️  NCC disabled (enable for serverless compute)"}
       ${var.enable_cmk_managed_services ? "- ✅ Customer-Managed Keys (Managed Services)" : ""}
       ${var.enable_cmk_managed_disks ? "- ✅ Customer-Managed Keys (Managed Disks)" : ""}
       ${var.enable_cmk_dbfs_root ? "- ✅ Customer-Managed Keys (DBFS Root)" : ""}
    
    5. Review Documentation:
       - Pattern docs: docs/patterns/FULL-PRIVATE.md
       - Troubleshooting: docs/TROUBLESHOOTING.md
       - Deployment checklist: docs/DEPLOYMENT-CHECKLIST.md
    
    EOT
}
