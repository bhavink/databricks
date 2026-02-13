# ==============================================
# Private DNS Zones for Databricks
# ==============================================

# DNS Zone for Databricks Control Plane (UI/API)
resource "azurerm_private_dns_zone" "databricks" {
  name                = "privatelink.azuredatabricks.net"
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

# Link Databricks DNS zone to customer VNet
resource "azurerm_private_dns_zone_virtual_network_link" "databricks" {
  name                  = "${var.workspace_prefix}-databricks-vnet-link"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.databricks.name
  virtual_network_id    = var.vnet_id
  tags                  = var.tags
}

# ==============================================
# Private DNS Zones for Storage
# ==============================================

# DNS Zone for ADLS Gen2 DFS (Data Lake Storage)
resource "azurerm_private_dns_zone" "dfs" {
  name                = "privatelink.dfs.core.windows.net"
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

# Link DFS DNS zone to customer VNet
resource "azurerm_private_dns_zone_virtual_network_link" "dfs" {
  name                  = "${var.workspace_prefix}-dfs-vnet-link"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.dfs.name
  virtual_network_id    = var.vnet_id
  tags                  = var.tags
}

# DNS Zone for Blob Storage
resource "azurerm_private_dns_zone" "blob" {
  name                = "privatelink.blob.core.windows.net"
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

# Link Blob DNS zone to customer VNet
resource "azurerm_private_dns_zone_virtual_network_link" "blob" {
  name                  = "${var.workspace_prefix}-blob-vnet-link"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.blob.name
  virtual_network_id    = var.vnet_id
  tags                  = var.tags
}

# ==============================================
# Databricks Front-End Private Endpoints
# ==============================================

# Private Endpoint for Databricks Data Plane to Control Plane (DP-CP)
resource "azurerm_private_endpoint" "databricks_ui_api" {
  name                = "${var.workspace_prefix}-dpcp-private-endpoint"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.privatelink_subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "${var.workspace_prefix}-dpcp-connection"
    private_connection_resource_id = var.workspace_id
    is_manual_connection           = false
    subresource_names              = ["databricks_ui_api"]
  }

  private_dns_zone_group {
    name                 = "databricks-ui-api-dns-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.databricks.id]
  }
}

# Private Endpoint for Browser Authentication
resource "azurerm_private_endpoint" "browser_authentication" {
  name                = "${var.workspace_prefix}-auth-private-endpoint"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.privatelink_subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "${var.workspace_prefix}-auth-connection"
    private_connection_resource_id = var.workspace_id
    is_manual_connection           = false
    subresource_names              = ["browser_authentication"]
  }

  private_dns_zone_group {
    name                 = "browser-auth-dns-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.databricks.id]
  }

  depends_on = [azurerm_private_endpoint.databricks_ui_api]
}

# ==============================================
# DBFS Storage Private Endpoints
# ==============================================

# Private Endpoint for DBFS DFS (Data Lake Storage)
resource "azurerm_private_endpoint" "dbfs_dfs" {
  name                = "${var.workspace_prefix}-dbfs-dfs-private-endpoint"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.privatelink_subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "${var.workspace_prefix}-dbfs-dfs-connection"
    private_connection_resource_id = "${var.workspace_managed_resource_group_id}/providers/Microsoft.Storage/storageAccounts/${var.dbfs_storage_name}"
    subresource_names              = ["dfs"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "dbfs-dfs-dns-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.dfs.id]
  }

  depends_on = [
    azurerm_private_dns_zone_virtual_network_link.dfs
  ]
}

# Private Endpoint for DBFS Blob
resource "azurerm_private_endpoint" "dbfs_blob" {
  name                = "${var.workspace_prefix}-dbfs-blob-private-endpoint"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.privatelink_subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "${var.workspace_prefix}-dbfs-blob-connection"
    private_connection_resource_id = "${var.workspace_managed_resource_group_id}/providers/Microsoft.Storage/storageAccounts/${var.dbfs_storage_name}"
    subresource_names              = ["blob"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "dbfs-blob-dns-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.blob.id]
  }

  depends_on = [
    azurerm_private_dns_zone_virtual_network_link.blob,
    azurerm_private_endpoint.dbfs_dfs
  ]
}

# ==============================================
# Unity Catalog Metastore Storage Private Endpoints
# ==============================================

# Private Endpoint for UC Metastore DFS
resource "azurerm_private_endpoint" "uc_metastore_dfs" {
  count               = var.enable_uc_storage_private_endpoints && var.create_uc_metastore_storage ? 1 : 0
  name                = "${var.workspace_prefix}-uc-metastore-dfs-private-endpoint"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.privatelink_subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "${var.workspace_prefix}-uc-metastore-dfs-connection"
    private_connection_resource_id = var.uc_metastore_storage_account_id
    subresource_names              = ["dfs"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "uc-metastore-dfs-dns-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.dfs.id]
  }

  depends_on = [
    azurerm_private_dns_zone_virtual_network_link.dfs
  ]
}

# Private Endpoint for UC Metastore Blob
resource "azurerm_private_endpoint" "uc_metastore_blob" {
  count               = var.enable_uc_storage_private_endpoints && var.create_uc_metastore_storage ? 1 : 0
  name                = "${var.workspace_prefix}-uc-metastore-blob-private-endpoint"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.privatelink_subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "${var.workspace_prefix}-uc-metastore-blob-connection"
    private_connection_resource_id = var.uc_metastore_storage_account_id
    subresource_names              = ["blob"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "uc-metastore-blob-dns-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.blob.id]
  }

  depends_on = [
    azurerm_private_dns_zone_virtual_network_link.blob,
    azurerm_private_endpoint.uc_metastore_dfs
  ]
}

# ==============================================
# Unity Catalog External Storage Private Endpoints
# ==============================================

# Private Endpoint for UC External Storage DFS
resource "azurerm_private_endpoint" "uc_external_dfs" {
  count               = var.enable_uc_storage_private_endpoints ? 1 : 0
  name                = "${var.workspace_prefix}-uc-external-dfs-private-endpoint"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.privatelink_subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "${var.workspace_prefix}-uc-external-dfs-connection"
    private_connection_resource_id = var.uc_external_storage_account_id
    subresource_names              = ["dfs"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "uc-external-dfs-dns-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.dfs.id]
  }

  depends_on = [
    azurerm_private_dns_zone_virtual_network_link.dfs
  ]
}

# Private Endpoint for UC External Storage Blob
resource "azurerm_private_endpoint" "uc_external_blob" {
  count               = var.enable_uc_storage_private_endpoints ? 1 : 0
  name                = "${var.workspace_prefix}-uc-external-blob-private-endpoint"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.privatelink_subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "${var.workspace_prefix}-uc-external-blob-connection"
    private_connection_resource_id = var.uc_external_storage_account_id
    subresource_names              = ["blob"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "uc-external-blob-dns-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.blob.id]
  }

  depends_on = [
    azurerm_private_dns_zone_virtual_network_link.blob,
    azurerm_private_endpoint.uc_external_dfs
  ]
}
