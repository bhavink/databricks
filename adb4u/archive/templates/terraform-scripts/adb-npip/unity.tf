***REMOVED*** locals {
***REMOVED*** ***REMOVED***   resource_regex            = "(?i)subscriptions/(.+)/resourceGroups/(.+)/providers/Microsoft.Databricks/workspaces/(.+)"
***REMOVED***   subscription_id           = var.subscription_id
***REMOVED***   resource_group            = azurerm_resource_group.adb_rg.name
***REMOVED***   databricks_workspace_name = azurerm_databricks_workspace.adb_ws.name
***REMOVED***   tenant_id                 = data.azurerm_client_config.current.tenant_id
***REMOVED***   databricks_workspace_host = azurerm_databricks_workspace.adb_ws.workspace_url
***REMOVED***   databricks_workspace_id   = azurerm_databricks_workspace.adb_ws.workspace_id
***REMOVED***   prefix                    = replace(replace(lower(azurerm_resource_group.adb_rg.name), "rg", ""), "-", "")
***REMOVED*** }

data "azurerm_client_config" "current" {
}


resource "azurerm_databricks_access_connector" "unity" {
  name                = "${var.prefix}-databricks-mi"
  resource_group_name = azurerm_resource_group.adb_rg.name
  location            = azurerm_resource_group.adb_rg.location
  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_storage_account" "unity_catalog" {
  name                     = "${var.prefix}storageroot"
  resource_group_name      = azurerm_resource_group.adb_rg.name
  location                 = azurerm_resource_group.adb_rg.location
  tags                     = azurerm_resource_group.adb_rg.tags
  account_tier             = "Standard"
  account_replication_type = "GRS"
  is_hns_enabled           = true
}

resource "azurerm_storage_container" "unity_catalog" {
  name                  = "${var.prefix}-container"
  storage_account_name  = azurerm_storage_account.unity_catalog.name
  container_access_type = "private"
}

resource "azurerm_role_assignment" "adb_ws" {
  scope                = azurerm_storage_account.unity_catalog.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_databricks_access_connector.unity.identity[0].principal_id
}

resource "databricks_metastore" "this" {
  provider = databricks.accounts
  name     = "primary"
  storage_root = format("abfss://%s@%s.dfs.core.windows.net/",
    azurerm_storage_container.unity_catalog.name,
  azurerm_storage_account.unity_catalog.name)
  force_destroy = true
  region        = azurerm_resource_group.adb_rg.location
}

resource "databricks_metastore_data_access" "first" {
  provider     = databricks.accounts
  metastore_id = databricks_metastore.this.id
  name         = "the-keys"
  azure_managed_identity {
    access_connector_id = azurerm_databricks_access_connector.unity.id
  }

  is_default = true
}

resource "databricks_metastore_assignment" "this" {
  provider             = databricks.accounts
  workspace_id         = azurerm_databricks_workspace.adb_ws.workspace_id
  metastore_id         = databricks_metastore.this.id
  default_catalog_name = "hive_metastore"

  depends_on = [
    azurerm_databricks_workspace.adb_ws
  ]
}