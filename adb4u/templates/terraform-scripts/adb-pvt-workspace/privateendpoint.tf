# Creates a DNS zone for Databricks workspace private endpoints.
resource "azurerm_private_dns_zone" "dnsdpcp" {
  name                = "privatelink.azuredatabricks.net"
  resource_group_name = azurerm_resource_group.this.name
}

# Creates a Private Endpoint (PE) for connecting from the classic Data Plane to Control Plane (DP to CP).
# - `name`: Unique name for the endpoint.
# - `location` and `resource_group_name`: Inherit from the resource group configuration.
# - `subnet_id`: Points to the private link subnet in the Databricks spoke virtual network.
resource "azurerm_private_endpoint" "dpcp" {
  name                = "dpcppvtendpoint"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  subnet_id           = azurerm_subnet.plsubnet.id

  private_service_connection {
    name                           = "ple-${var.workspace_prefix}-dpcp"
    private_connection_resource_id = azurerm_databricks_workspace.this.id
    is_manual_connection           = false
    subresource_names              = ["databricks_ui_api"]
  }

  private_dns_zone_group {
    name                 = "private-dns-zone-dpcp"
    private_dns_zone_ids = [azurerm_private_dns_zone.dnsdpcp.id]
  }
}


# Creates a Private Endpoint for browser-based authentication.
# - Depends on the DP-CP private endpoint.
# - Subresource name set to `browser_authentication`.

resource "azurerm_private_endpoint" "auth" {
  name                = "aadauthpvtendpoint"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  subnet_id           = azurerm_subnet.plsubnet.id

  private_service_connection {
    name                           = "ple-${var.workspace_prefix}-auth"
    private_connection_resource_id = azurerm_databricks_workspace.this.id
    is_manual_connection           = false
    subresource_names              = ["browser_authentication"]
  }

  private_dns_zone_group {
    name                 = "private-dns-zone-auth"
    private_dns_zone_ids = [azurerm_private_dns_zone.dnsdpcp.id]
  }
  depends_on = [
    azurerm_private_endpoint.dpcp
  ]
}

# Links the DNS zone for DP-CP connections to the spoke virtual network.
resource "azurerm_private_dns_zone_virtual_network_link" "dpcpdnszonevnetlink" {
  name                  = "dpcpspokevnetconnection"
  resource_group_name   = azurerm_resource_group.this.name
  private_dns_zone_name = azurerm_private_dns_zone.dnsdpcp.name
  virtual_network_id    = azurerm_virtual_network.this.id
}

# Create the Private DNS Zone for ADLS Gen2 DFS
resource "azurerm_private_dns_zone" "this_dfs" {
  name                = "privatelink.dfs.core.windows.net"
  resource_group_name = azurerm_resource_group.this.name
}

# Links ADLS Gen2 DFS DNS zone to the spoke virtual network.
resource "azurerm_private_dns_zone_virtual_network_link" "dnszonevnetlink1" {
  name                  = "dfs-vnet-link-connection"
  resource_group_name   = azurerm_resource_group.this.name
  private_dns_zone_name = azurerm_private_dns_zone.this_dfs.name
  virtual_network_id    = azurerm_virtual_network.this.id
}

# Create the Private DNS Zone for ADLS Gen2 BLOB
resource "azurerm_private_dns_zone" "this_blob" {
  name                = "privatelink.blob.core.windows.net"
  resource_group_name = azurerm_resource_group.this.name
}

# Links ADLS Gen2 BLOB DNS zone to the spoke virtual network.
resource "azurerm_private_dns_zone_virtual_network_link" "dnszonevnetlink2" {
  name                  = "blob-vnet-link-connection"
  resource_group_name   = azurerm_resource_group.this.name
  private_dns_zone_name = azurerm_private_dns_zone.this_blob.name
  virtual_network_id    = azurerm_virtual_network.this.id
}


# Create the Private Endpoint for UC ROOT DFS sub resource
resource "azurerm_private_endpoint" "uc_root_storage_dfs_pe" {
  name                = "uc-root-dfs-pvt-endpoint"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  subnet_id           = azurerm_subnet.plsubnet.id

  private_service_connection {
    name                           = "ple-${var.workspace_prefix}-uc-root"
    private_connection_resource_id = join("", [azurerm_resource_group.this.id, "/providers/Microsoft.Storage/storageAccounts/${azurerm_storage_account.uc_root_storage.name}"])
    subresource_names              = ["dfs"]
    is_manual_connection           = false
  }
  private_dns_zone_group {
    name                 = "private-dns-zone-dfs"
    private_dns_zone_ids = [azurerm_private_dns_zone.this_dfs.id]
  }
  depends_on = [
    azurerm_private_dns_zone_virtual_network_link.dnszonevnetlink1
  ]
}

# Create the Private Endpoint for DBFS DFS sub resource
resource "azurerm_private_endpoint" "dbfs_storage_dfs_pe" {
  name                = "dbfs-dfs-pvt-endpoint"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  subnet_id           = azurerm_subnet.plsubnet.id

  private_service_connection {
    name                           = "ple-${var.workspace_prefix}-dbfs"
    private_connection_resource_id = join("", [azurerm_databricks_workspace.this.managed_resource_group_id, "/providers/Microsoft.Storage/storageAccounts/${local.dbfsname}"])
    subresource_names              = ["dfs"]
    is_manual_connection           = false
  }
  private_dns_zone_group {
    name                 = "private-dns-zone-dfs"
    private_dns_zone_ids = [azurerm_private_dns_zone.this_dfs.id]
  }
  depends_on = [
    azurerm_private_endpoint.uc_root_storage_dfs_pe
  ]
}

# Create the Private Endpoint for UC ROOT BLOB sub resource
resource "azurerm_private_endpoint" "uc_root_storage_blob_pe" {
  name                = "uc-root-blob-pvt-endpoint"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  subnet_id           = azurerm_subnet.plsubnet.id

  private_service_connection {
    name                           = "ple-${var.workspace_prefix}-uc-root"
    private_connection_resource_id = join("", [azurerm_resource_group.this.id, "/providers/Microsoft.Storage/storageAccounts/${azurerm_storage_account.uc_root_storage.name}"])
    subresource_names              = ["blob"]
    is_manual_connection           = false
  }
  private_dns_zone_group {
    name                 = "private-dns-zone-blob"
    private_dns_zone_ids = [azurerm_private_dns_zone.this_blob.id]
  }
  depends_on = [
    azurerm_private_dns_zone_virtual_network_link.dnszonevnetlink2
  ]
}

# Create the Private Endpoint for DBFS BLOB sub resource
resource "azurerm_private_endpoint" "dbfs_storage_blob_pe" {
  name                = "dbfs-blob-pvt-endpoint"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  subnet_id           = azurerm_subnet.plsubnet.id

  private_service_connection {
    name                           = "ple-${var.workspace_prefix}-dbfs"
    private_connection_resource_id = join("", [azurerm_databricks_workspace.this.managed_resource_group_id, "/providers/Microsoft.Storage/storageAccounts/${local.dbfsname}"])
    subresource_names              = ["blob"]
    is_manual_connection           = false
  }
  private_dns_zone_group {
    name                 = "private-dns-zone-blob"
    private_dns_zone_ids = [azurerm_private_dns_zone.this_blob.id]
  }
  depends_on = [
    azurerm_private_endpoint.uc_root_storage_blob_pe
  ]
}