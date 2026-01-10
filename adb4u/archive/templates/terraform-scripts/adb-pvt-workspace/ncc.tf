# Creates a Network Connectivity Configuration (NCC) in Databricks for managing network settings.
# - `name`: Unique name for the configuration using a prefix.
# - `region`: The Azure region where this configuration will be applied.
resource "databricks_mws_network_connectivity_config" "ncc" {
  provider = databricks.accounts
  name     = "${local.prefix}-ncc"
  region   = var.rglocation
}

# Binds the created NCC configuration to the specified Databricks workspace.
# - `network_connectivity_config_id`: References the NCC configuration created earlier.
# - `workspace_id`: Specifies the Databricks workspace to which the NCC is bound.
resource "databricks_mws_ncc_binding" "ws_ncc_binding" {
  provider                       = databricks.accounts
  network_connectivity_config_id = databricks_mws_network_connectivity_config.ncc.network_connectivity_config_id
  workspace_id                   = azurerm_databricks_workspace.this.workspace_id
}

# Creates a Private Endpoint (PE) rule in Databricks for blob storage access on external storage.
# - `resource_id`: Specifies the Azure resource ID of the external storage account.
# - `group_id`: Defines the PE group for Azure blob access.
resource "databricks_mws_ncc_private_endpoint_rule" "uc_ext_storage_blob_ncc_pe1" {
  provider                       = databricks.accounts
  network_connectivity_config_id = databricks_mws_network_connectivity_config.ncc.network_connectivity_config_id
  resource_id                    = azurerm_storage_account.uc_ext_storage.id
  group_id                       = "blob"
}

# Creates a Private Endpoint (PE) rule in Databricks for Data Lake Storage (DFS) access on external storage.
# - `resource_id`: Specifies the Azure resource ID of the external storage account.
# - `group_id`: Defines the PE group for Azure DFS access.
resource "databricks_mws_ncc_private_endpoint_rule" "uc_ext_storage_dfs_ncc_pe1" {
  provider                       = databricks.accounts
  network_connectivity_config_id = databricks_mws_network_connectivity_config.ncc.network_connectivity_config_id
  resource_id                    = azurerm_storage_account.uc_ext_storage.id
  group_id                       = "dfs"
}

# Creates a Private Endpoint (PE) rule for blob storage access on root storage.
# - `resource_id`: Specifies the Azure resource ID of the root storage account.
# - `group_id`: Defines the PE group for Azure blob access.
resource "databricks_mws_ncc_private_endpoint_rule" "uc_root_storage_blob_ncc_pe2" {
  provider                       = databricks.accounts
  network_connectivity_config_id = databricks_mws_network_connectivity_config.ncc.network_connectivity_config_id
  resource_id                    = azurerm_storage_account.uc_root_storage.id
  group_id                       = "blob"
}

# Creates a Private Endpoint (PE) rule for Data Lake Storage (DFS) access on root storage.
# - `resource_id`: Specifies the Azure resource ID of the root storage account.
# - `group_id`: Defines the PE group for Azure DFS access.
resource "databricks_mws_ncc_private_endpoint_rule" "uc_root_storage_dfs_ncc_pe1" {
  provider                       = databricks.accounts
  network_connectivity_config_id = databricks_mws_network_connectivity_config.ncc.network_connectivity_config_id
  resource_id                    = azurerm_storage_account.uc_root_storage.id
  group_id                       = "dfs"
}

# Creates a Private Endpoint (PE) rule for blob storage access on DBFS storage.
# - `resource_id`: Constructs the resource ID for the DBFS storage account based on the workspace's managed resource group.
# - `group_id`: Defines the PE group for Azure blob access.
resource "databricks_mws_ncc_private_endpoint_rule" "dbfs_storage_blob_ncc_pe" {
  provider                       = databricks.accounts
  network_connectivity_config_id = databricks_mws_network_connectivity_config.ncc.network_connectivity_config_id
  resource_id                    = join("", [azurerm_databricks_workspace.this.managed_resource_group_id, "/providers/Microsoft.Storage/storageAccounts/${local.dbfsname}"])
  group_id                       = "blob"
}

# Creates a Private Endpoint (PE) rule for Data Lake Storage (DFS) access on DBFS storage.
# - `resource_id`: Constructs the resource ID for the DBFS storage account based on the workspace's managed resource group.
# - `group_id`: Defines the PE group for Azure DFS access.
resource "databricks_mws_ncc_private_endpoint_rule" "dbfs_storage_dfs_ncc_pe" {
  provider                       = databricks.accounts
  network_connectivity_config_id = databricks_mws_network_connectivity_config.ncc.network_connectivity_config_id
  resource_id                    = join("", [azurerm_databricks_workspace.this.managed_resource_group_id, "/providers/Microsoft.Storage/storageAccounts/${local.dbfsname}"])
  group_id                       = "dfs"
}
