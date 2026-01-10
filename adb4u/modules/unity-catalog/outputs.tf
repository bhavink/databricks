# ==============================================
# Unity Catalog Outputs
# ==============================================

output "metastore_id" {
  description = "Unity Catalog metastore ID"
  value       = local.metastore_id
}

output "metastore_name" {
  description = "Unity Catalog metastore name"
  value       = var.create_metastore ? databricks_metastore.this[0].name : "existing-metastore"
}

output "workspace_metastore_assignment_id" {
  description = "Workspace metastore assignment ID"
  value       = databricks_metastore_assignment.this.id
}

# ==============================================
# Storage Outputs
# ==============================================

output "metastore_storage_account_id" {
  description = "Metastore root storage account ID"
  value       = var.create_metastore_storage ? azurerm_storage_account.metastore[0].id : null
}

output "metastore_storage_account_name" {
  description = "Metastore root storage account name"
  value       = var.create_metastore_storage ? azurerm_storage_account.metastore[0].name : null
}

output "external_storage_account_id" {
  description = "External location storage account ID"
  value       = var.create_external_location_storage ? azurerm_storage_account.external[0].id : null
}

output "external_storage_account_name" {
  description = "External location storage account name"
  value       = var.create_external_location_storage ? azurerm_storage_account.external[0].name : null
}

# ==============================================
# Storage Account FQDNs
# ==============================================

output "storage_account_fqdns" {
  description = "List of Unity Catalog storage account FQDNs"
  value = concat(
    var.create_metastore_storage ? ["${azurerm_storage_account.metastore[0].name}.dfs.core.windows.net"] : [],
    var.create_external_location_storage ? ["${azurerm_storage_account.external[0].name}.dfs.core.windows.net"] : []
  )
}

output "external_location_name" {
  description = "External location name in Unity Catalog"
  value       = var.create_external_location_storage ? databricks_external_location.this[0].name : null
}

output "external_location_url" {
  description = "External location URL (ABFSS path)"
  value       = var.create_external_location_storage ? databricks_external_location.this[0].url : null
}

# ==============================================
# Access Connector Outputs
# ==============================================

output "access_connector_id" {
  description = "Access Connector resource ID"
  value       = local.access_connector_id
}

output "access_connector_principal_id" {
  description = "Access Connector managed identity principal ID"
  value       = local.access_connector_principal_id
}

# ==============================================
# Storage Credential Outputs
# ==============================================

output "storage_credential_name" {
  description = "Storage credential name for external locations"
  value       = var.create_external_location_storage ? databricks_storage_credential.external[0].name : null
}

# ==============================================
# Configuration Summary
# ==============================================

output "unity_catalog_configuration" {
  description = "Summary of Unity Catalog configuration"
  value = {
    metastore_created         = var.create_metastore
    metastore_id              = local.metastore_id
    access_connector_created  = var.create_access_connector
    storage_connectivity      = var.enable_private_link_storage ? "Private Link" : "Service Endpoints"
    external_location_created = var.create_external_location_storage
  }
}
