resource "databricks_mws_network_connectivity_config" "ncc" {
  provider = databricks.accounts
  name     = "ncc-for-${local.prefix}"
  region   = var.rglocation
}

resource "databricks_mws_ncc_binding" "ncc_binding" {
  provider                       = databricks.accounts
  network_connectivity_config_id = databricks_mws_network_connectivity_config.ncc.network_connectivity_config_id
  workspace_id                   = azurerm_databricks_workspace.this.workspace_id
}

//PL to customer managed UC external storage
resource "databricks_mws_ncc_private_endpoint_rule" "uc_ext_storage1_blob" {
  provider                       = databricks.accounts
  network_connectivity_config_id = databricks_mws_network_connectivity_config.ncc.network_connectivity_config_id
  resource_id                    = azurerm_storage_account.uc_ext_storage.id
  group_id                       = "blob"
}
resource "databricks_mws_ncc_private_endpoint_rule" "uc_ext_storage1_dfs" {
  provider                       = databricks.accounts
  network_connectivity_config_id = databricks_mws_network_connectivity_config.ncc.network_connectivity_config_id
  resource_id                    = azurerm_storage_account.uc_ext_storage.id
  group_id                       = "dfs"
}

//PL to customer managed UC root storage
resource "databricks_mws_ncc_private_endpoint_rule" "uc_root_storage_blob" {
  provider                       = databricks.accounts
  network_connectivity_config_id = databricks_mws_network_connectivity_config.ncc.network_connectivity_config_id
  resource_id                    = azurerm_storage_account.uc_root_storage.id
  group_id                       = "blob"
}
resource "databricks_mws_ncc_private_endpoint_rule" "uc_root_storage_dfs" {
  provider                       = databricks.accounts
  network_connectivity_config_id = databricks_mws_network_connectivity_config.ncc.network_connectivity_config_id
  resource_id                    = azurerm_storage_account.uc_root_storage.id
  group_id                       = "dfs"
}

//PL to workspace dbfs storage
resource "databricks_mws_ncc_private_endpoint_rule" "dbfs_storage_blob" {
  provider                       = databricks.accounts
  network_connectivity_config_id = databricks_mws_network_connectivity_config.ncc.network_connectivity_config_id
  resource_id                    = join("", [azurerm_databricks_workspace.this.managed_resource_group_id, "/providers/Microsoft.Storage/storageAccounts/${local.dbfsname}"])
  group_id                       = "blob"
}
resource "databricks_mws_ncc_private_endpoint_rule" "dbfs_storage_dfs" {
  provider                       = databricks.accounts
  network_connectivity_config_id = databricks_mws_network_connectivity_config.ncc.network_connectivity_config_id
  resource_id                    = join("", [azurerm_databricks_workspace.this.managed_resource_group_id, "/providers/Microsoft.Storage/storageAccounts/${local.dbfsname}"])
  group_id                       = "dfs"
}