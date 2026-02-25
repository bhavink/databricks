# ==============================================
# Private DNS Zones
# ==============================================

output "private_dns_zones" {
  description = "Private DNS zone IDs"
  value = {
    databricks = azurerm_private_dns_zone.databricks.id
    dfs        = azurerm_private_dns_zone.dfs.id
    blob       = azurerm_private_dns_zone.blob.id
  }
}

# ==============================================
# Databricks Private Endpoints
# ==============================================

output "databricks_ui_api_private_endpoint_id" {
  description = "Private Endpoint ID for Databricks UI/API (DP-CP)"
  value       = azurerm_private_endpoint.databricks_ui_api.id
}

output "browser_authentication_private_endpoint_id" {
  description = "Private Endpoint ID for Browser Authentication"
  value       = azurerm_private_endpoint.browser_authentication.id
}

# ==============================================
# DBFS Storage Private Endpoints
# ==============================================

output "dbfs_dfs_private_endpoint_id" {
  description = "Private Endpoint ID for DBFS DFS"
  value       = azurerm_private_endpoint.dbfs_dfs.id
}

output "dbfs_blob_private_endpoint_id" {
  description = "Private Endpoint ID for DBFS Blob"
  value       = azurerm_private_endpoint.dbfs_blob.id
}

# ==============================================
# Unity Catalog Storage Private Endpoints
# ==============================================

output "uc_metastore_dfs_private_endpoint_id" {
  description = "Private Endpoint ID for UC Metastore DFS (null if not created)"
  value       = var.enable_uc_storage_private_endpoints && var.create_uc_metastore_storage ? azurerm_private_endpoint.uc_metastore_dfs[0].id : null
}

output "uc_metastore_blob_private_endpoint_id" {
  description = "Private Endpoint ID for UC Metastore Blob (null if not created)"
  value       = var.enable_uc_storage_private_endpoints && var.create_uc_metastore_storage ? azurerm_private_endpoint.uc_metastore_blob[0].id : null
}

output "uc_external_dfs_private_endpoint_id" {
  description = "Private Endpoint ID for UC External Storage DFS (null if not created)"
  value       = var.enable_uc_storage_private_endpoints ? azurerm_private_endpoint.uc_external_dfs[0].id : null
}

output "uc_external_blob_private_endpoint_id" {
  description = "Private Endpoint ID for UC External Storage Blob (null if not created)"
  value       = var.enable_uc_storage_private_endpoints ? azurerm_private_endpoint.uc_external_blob[0].id : null
}

# ==============================================
# Configuration Summary
# ==============================================

output "private_endpoints_summary" {
  description = "Summary of Private Endpoints configuration"
  value = {
    databricks_ui_api_created      = true
    browser_authentication_created = true
    dbfs_dfs_created               = true
    dbfs_blob_created              = true
    uc_metastore_dfs_created       = var.enable_uc_storage_private_endpoints && var.create_uc_metastore_storage
    uc_metastore_blob_created      = var.enable_uc_storage_private_endpoints && var.create_uc_metastore_storage
    uc_external_dfs_created        = var.enable_uc_storage_private_endpoints
    uc_external_blob_created       = var.enable_uc_storage_private_endpoints
    total_private_endpoints        = 4 + (var.enable_uc_storage_private_endpoints && var.create_uc_metastore_storage ? 2 : 0) + (var.enable_uc_storage_private_endpoints ? 2 : 0)
    private_dns_zones_created      = 3
  }
}
