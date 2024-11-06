//classic-dp-to-cp pvt endpoint
resource "azurerm_private_endpoint" "dpcp" {
  name                = "dpcppvtendpoint"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  subnet_id           = azurerm_subnet.plsubnet.id //private link subnet, in databricks spoke vnet

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

//browser-auth pvt endpoint
resource "azurerm_private_endpoint" "auth" {
  name                = "aadauthpvtendpoint"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  subnet_id           = azurerm_subnet.plsubnet.id //private link subnet, in databricks spoke vnet

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

// dns for db workspace pvt endpoints
resource "azurerm_private_dns_zone" "dnsdpcp" {
  name                = "privatelink.azuredatabricks.net"
  resource_group_name = azurerm_resource_group.this.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "dpcpdnszonevnetlink" {
  name                  = "dpcpspokevnetconnection"
  resource_group_name   = azurerm_resource_group.this.name
  private_dns_zone_name = azurerm_private_dns_zone.dnsdpcp.name
  virtual_network_id    = azurerm_virtual_network.this.id // connect to spoke vnet
}


//dbfs blob sub-resource pvt endpoint
resource "azurerm_private_endpoint" "dbfspe1" {
  name                = "dbfspvtendpoint1"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  subnet_id           = azurerm_subnet.plsubnet.id //private link subnet, in databricks spoke vnet

  private_service_connection {
    name                           = "ple-${var.workspace_prefix}-dbfs"
    private_connection_resource_id = join("", [azurerm_databricks_workspace.this.managed_resource_group_id, "/providers/Microsoft.Storage/storageAccounts/${local.dbfsname}"])
    is_manual_connection           = false
    subresource_names              = ["blob"]
  }

  private_dns_zone_group {
    name                 = "private-dns-zone-dbfs-blob"
    private_dns_zone_ids = [azurerm_private_dns_zone.dnsdbfs1.id]
  }
}
resource "azurerm_private_dns_zone" "dnsdbfs1" {
  name                = "privatelink.blob.core.windows.net"
  resource_group_name = azurerm_resource_group.this.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "dbfsdnszonevnetlink1" {
  name                  = "dbfsspokevnetconnection1"
  resource_group_name   = azurerm_resource_group.this.name
  private_dns_zone_name = azurerm_private_dns_zone.dnsdbfs1.name
  virtual_network_id    = azurerm_virtual_network.this.id // connect to spoke vnet
}

//dbfs dfs sub-resource pvt endpoint
resource "azurerm_private_endpoint" "dbfspe2" {
  name                = "dbfspvtendpoint2"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  subnet_id           = azurerm_subnet.plsubnet.id //private link subnet, in databricks spoke vnet


  private_service_connection {
    name                           = "ple-${var.workspace_prefix}-dbfs"
    private_connection_resource_id = join("", [azurerm_databricks_workspace.this.managed_resource_group_id, "/providers/Microsoft.Storage/storageAccounts/${local.dbfsname}"])
    is_manual_connection           = false
    subresource_names              = ["dfs"]
  }

  private_dns_zone_group {
    name                 = "private-dns-zone-dbfs-dfs"
    private_dns_zone_ids = [azurerm_private_dns_zone.dnsdbfs2.id]
  }
}
resource "azurerm_private_dns_zone" "dnsdbfs2" {
  name                = "privatelink.dfs.core.windows.net"
  resource_group_name = azurerm_resource_group.this.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "dbfsdnszonevnetlink2" {
  name                  = "dbfsspokevnetconnection2"
  resource_group_name   = azurerm_resource_group.this.name
  private_dns_zone_name = azurerm_private_dns_zone.dnsdbfs2.name
  virtual_network_id    = azurerm_virtual_network.this.id // connect to spoke vnet
}
