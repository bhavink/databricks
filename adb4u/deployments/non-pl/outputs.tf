# ==============================================
# Workspace Outputs
# ==============================================

output "workspace_id" {
  description = "Databricks workspace ID"
  value       = module.workspace.workspace_id
}

output "workspace_url" {
  description = "Databricks workspace URL"
  value       = module.workspace.workspace_url
}

output "workspace_name" {
  description = "Databricks workspace name"
  value       = module.workspace.workspace_name
}

# ==============================================
# Network Outputs
# ==============================================

output "vnet_id" {
  description = "Virtual Network ID"
  value       = module.networking.vnet_id
}

output "vnet_name" {
  description = "Virtual Network name"
  value       = module.networking.vnet_name
}

output "subnet_ids" {
  description = "Subnet IDs (public, private)"
  value       = module.networking.subnet_ids
}

output "nat_gateway_public_ip" {
  description = "NAT Gateway public IP address"
  value       = module.networking.nat_gateway_public_ip
}

# ==============================================
# Unity Catalog Outputs
# ==============================================

output "metastore_id" {
  description = "Unity Catalog metastore ID"
  value       = module.unity_catalog.metastore_id
}

output "metastore_name" {
  description = "Unity Catalog metastore name"
  value       = module.unity_catalog.metastore_name
}

output "external_location_name" {
  description = "External location name"
  value       = module.unity_catalog.external_location_name
}

output "external_location_url" {
  description = "External location URL (ABFSS path)"
  value       = module.unity_catalog.external_location_url
}

output "external_storage_account_name" {
  description = "External location storage account name"
  value       = module.unity_catalog.external_storage_account_name
}

# ==============================================
# Configuration Summary
# ==============================================

output "deployment_summary" {
  description = "Summary of deployment configuration"
  value = {
    pattern              = "Non-PL (Public Control Plane + NPIP Data Plane)"
    workspace_id         = module.workspace.workspace_id
    workspace_url        = module.workspace.workspace_url
    region               = var.location
    nat_gateway_enabled  = var.enable_nat_gateway
    nat_gateway_ip       = module.networking.nat_gateway_public_ip
    cmk_enabled          = var.enable_cmk_managed_services || var.enable_cmk_managed_disks
    ip_access_lists      = var.enable_ip_access_lists
    unity_catalog        = module.unity_catalog.unity_catalog_configuration
    storage_connectivity = "Service Endpoints (Cost-Efficient)"
  }
}

# ==============================================
# Next Steps Output
# ==============================================

output "next_steps" {
  description = "Next steps for post-deployment configuration"
  value = <<-EOT
    
    ✅ Deployment Complete - Non-PL Pattern
    
    📋 Workspace Details:
       - Workspace URL: ${module.workspace.workspace_url}
       - Workspace ID: ${module.workspace.workspace_id}
       - Region: ${var.location}
    
    🌐 Network Configuration:
       - Pattern: Public Control Plane + NPIP Data Plane
       - NAT Gateway IP: ${module.networking.nat_gateway_public_ip != null ? module.networking.nat_gateway_public_ip : "Not enabled"}
       - Egress: Internet access via NAT Gateway (for PyPI, Maven, CRAN)
    
    🗄️ Unity Catalog:
       - Metastore ID: ${module.unity_catalog.metastore_id}
       - External Location: ${module.unity_catalog.external_location_name}
       - Storage: ${module.unity_catalog.external_storage_account_name}
    
    🔒 Security:
       - Secure Cluster Connectivity (NPIP): ✅ Enabled
       - Storage Connectivity: Service Endpoints
       - CMK: ${var.enable_cmk_managed_services || var.enable_cmk_managed_disks ? "✅ Enabled" : "⚠️  Disabled (optional)"}
       - IP Access Lists: ${var.enable_ip_access_lists ? "✅ Enabled" : "⚠️  Disabled (optional)"}
    
    📚 Next Steps:
       1. Access workspace: ${module.workspace.workspace_url}
       2. Configure Unity Catalog catalogs and schemas
       3. Create compute policies and clusters
       4. Set up workspace users/groups
       5. Configure data access permissions
    
    📖 Documentation: See README.md for detailed configuration options
  EOT
}
