***REMOVED*** ==============================================
***REMOVED*** Essential Outputs
***REMOVED*** ==============================================

output "workspace_id" {
  description = "Databricks workspace ID (Azure resource ID)"
  value       = azurerm_databricks_workspace.this.id
}

output "workspace_url" {
  description = "Databricks workspace URL"
  value       = "https://${azurerm_databricks_workspace.this.workspace_url}"
}

output "workspace_name" {
  description = "Databricks workspace name"
  value       = azurerm_databricks_workspace.this.name
}

output "managed_resource_group_id" {
  description = "Managed resource group ID (contains cluster VMs and storage)"
  value       = azurerm_databricks_workspace.this.managed_resource_group_id
}

output "managed_resource_group_name" {
  description = "Managed resource group name"
  value       = azurerm_databricks_workspace.this.managed_resource_group_name
}

output "workspace_id_numeric" {
  description = "Databricks workspace ID (numeric, for Unity Catalog assignment)"
  value       = azurerm_databricks_workspace.this.workspace_id
}

output "dbfs_storage_name" {
  description = "DBFS storage account name (from custom_parameters if set, otherwise Databricks-generated)"
  value       = try(azurerm_databricks_workspace.this.custom_parameters[0].storage_account_name, "databricks-managed")
}

output "dbfs_storage_account_id" {
  description = "DBFS storage account resource ID (required for Service Endpoint Policy)"
  value       = try(data.azurerm_resources.dbfs_storage.resources[0].id, null)
}

***REMOVED*** ==============================================
***REMOVED*** Configuration Outputs
***REMOVED*** ==============================================

output "workspace_configuration" {
  description = "Summary of workspace configuration"
  value = {
    name                          = azurerm_databricks_workspace.this.name
    sku                           = azurerm_databricks_workspace.this.sku
    location                      = azurerm_databricks_workspace.this.location
    public_network_access_enabled = azurerm_databricks_workspace.this.public_network_access_enabled
    npip_enabled                  = true  ***REMOVED*** Always enabled in our pattern
    cmk_managed_services_enabled  = var.enable_cmk_managed_services
    cmk_managed_disks_enabled     = var.enable_cmk_managed_disks
    cmk_dbfs_root_enabled         = var.enable_cmk_dbfs_root
    ip_access_lists_enabled       = var.enable_ip_access_lists
    allowed_ip_count              = var.enable_ip_access_lists ? length(var.allowed_ip_ranges) : 0
  }
}

***REMOVED*** ==============================================
***REMOVED*** Advanced Outputs (Full Objects)
***REMOVED*** ==============================================

output "workspace" {
  description = "Complete workspace object (for advanced use)"
  value       = azurerm_databricks_workspace.this
  sensitive   = true
}
