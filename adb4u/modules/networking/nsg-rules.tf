***REMOVED*** ==============================================
***REMOVED*** NSG Rules for Secure Cluster Connectivity (SCC/NPIP)
***REMOVED*** ==============================================
***REMOVED***
***REMOVED*** Reference: https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/vnet-inject***REMOVED***network-security-group-rules-for-workspaces
***REMOVED***
***REMOVED*** IMPORTANT: NSG rules are only created for PRIVATE LINK deployments.
***REMOVED*** - For Non-PL: Azure Databricks automatically creates these rules (with "Microsoft.Databricks-workspaces_UseOnly_" prefix)
***REMOVED*** - For Private Link: We must create these rules explicitly because public network access is disabled
***REMOVED***
***REMOVED*** NOTE: When SCC/NPIP is enabled, inbound rules on ports 22 and 5557 from 
***REMOVED*** AzureDatabricks service tag are NOT required (and would be security risk).
***REMOVED***
***REMOVED*** ==============================================

***REMOVED*** Get the NSG ID (works for both new and existing)
locals {
  nsg_id_for_rules = local.nsg_id
}

***REMOVED*** ==============================================
***REMOVED*** Inbound Rules
***REMOVED*** ==============================================

***REMOVED*** Allow inbound from VirtualNetwork to VirtualNetwork (Any protocol/port)
***REMOVED*** This enables internal cluster communication
***REMOVED*** Only create for Private Link deployments
resource "azurerm_network_security_rule" "inbound_vnet_to_vnet" {
  count = var.enable_private_link ? 1 : 0

  name                        = "AllowVnetInBound"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "VirtualNetwork"
  destination_address_prefix  = "VirtualNetwork"
  resource_group_name         = var.use_existing_network ? var.existing_resource_group_name : var.resource_group_name
  network_security_group_name = var.use_existing_network ? var.existing_nsg_name : azurerm_network_security_group.this[0].name

  depends_on = [
    azurerm_network_security_group.this
  ]
}

***REMOVED*** ==============================================
***REMOVED*** Outbound Rules
***REMOVED*** ==============================================

***REMOVED*** Allow outbound to AzureDatabricks service tag
***REMOVED*** Required ports: 443 (HTTPS), 3306 (MySQL), 8443-8451 (internal)
***REMOVED*** Only create for Private Link deployments
resource "azurerm_network_security_rule" "outbound_to_databricks" {
  count = var.enable_private_link ? 1 : 0

  name                        = "AllowDatabricksOutBound"
  priority                    = 100
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_ranges     = ["443", "3306", "8443", "8444", "8445", "8446", "8447", "8448", "8449", "8450", "8451"]
  source_address_prefix       = "VirtualNetwork"
  destination_address_prefix  = "AzureDatabricks"
  resource_group_name         = var.use_existing_network ? var.existing_resource_group_name : var.resource_group_name
  network_security_group_name = var.use_existing_network ? var.existing_nsg_name : azurerm_network_security_group.this[0].name

  depends_on = [
    azurerm_network_security_group.this
  ]
}

***REMOVED*** Allow outbound to SQL service tag (port 3306)
***REMOVED*** Required for metadata operations
***REMOVED*** Only create for Private Link deployments
resource "azurerm_network_security_rule" "outbound_to_sql" {
  count = var.enable_private_link ? 1 : 0

  name                        = "AllowSqlOutBound"
  priority                    = 101
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "3306"
  source_address_prefix       = "VirtualNetwork"
  destination_address_prefix  = "Sql"
  resource_group_name         = var.use_existing_network ? var.existing_resource_group_name : var.resource_group_name
  network_security_group_name = var.use_existing_network ? var.existing_nsg_name : azurerm_network_security_group.this[0].name

  depends_on = [
    azurerm_network_security_group.this
  ]
}

***REMOVED*** Allow outbound to Storage service tag (port 443)
***REMOVED*** Required for Unity Catalog and workspace storage
***REMOVED*** Only create for Private Link deployments
resource "azurerm_network_security_rule" "outbound_to_storage" {
  count = var.enable_private_link ? 1 : 0

  name                        = "AllowStorageOutBound"
  priority                    = 102
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "443"
  source_address_prefix       = "VirtualNetwork"
  destination_address_prefix  = "Storage"
  resource_group_name         = var.use_existing_network ? var.existing_resource_group_name : var.resource_group_name
  network_security_group_name = var.use_existing_network ? var.existing_nsg_name : azurerm_network_security_group.this[0].name

  depends_on = [
    azurerm_network_security_group.this
  ]
}

***REMOVED*** Allow outbound within VirtualNetwork (Any protocol/port)
***REMOVED*** Required for internal cluster communication
***REMOVED*** Only create for Private Link deployments
resource "azurerm_network_security_rule" "outbound_vnet_to_vnet" {
  count = var.enable_private_link ? 1 : 0

  name                        = "AllowVnetOutBound"
  priority                    = 103
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "VirtualNetwork"
  destination_address_prefix  = "VirtualNetwork"
  resource_group_name         = var.use_existing_network ? var.existing_resource_group_name : var.resource_group_name
  network_security_group_name = var.use_existing_network ? var.existing_nsg_name : azurerm_network_security_group.this[0].name

  depends_on = [
    azurerm_network_security_group.this
  ]
}

***REMOVED*** Allow outbound to EventHub service tag (port 9093)
***REMOVED*** Required for log delivery and diagnostics
***REMOVED*** Only create for Private Link deployments
resource "azurerm_network_security_rule" "outbound_to_eventhub" {
  count = var.enable_private_link ? 1 : 0

  name                        = "AllowEventHubOutBound"
  priority                    = 104
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "9093"
  source_address_prefix       = "VirtualNetwork"
  destination_address_prefix  = "EventHub"
  resource_group_name         = var.use_existing_network ? var.existing_resource_group_name : var.resource_group_name
  network_security_group_name = var.use_existing_network ? var.existing_nsg_name : azurerm_network_security_group.this[0].name

  depends_on = [
    azurerm_network_security_group.this
  ]
}

***REMOVED*** Optional: Allow outbound for library installs (ports 111, 2049)
***REMOVED*** Recommended by Databricks to enable certain library installations
***REMOVED*** Only create for Private Link deployments
resource "azurerm_network_security_rule" "outbound_for_library_installs" {
  count = var.enable_private_link ? 1 : 0

  name                        = "AllowLibraryInstallsOutBound"
  priority                    = 105
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_ranges     = ["111", "2049"]
  source_address_prefix       = "VirtualNetwork"
  destination_address_prefix  = "*"
  resource_group_name         = var.use_existing_network ? var.existing_resource_group_name : var.resource_group_name
  network_security_group_name = var.use_existing_network ? var.existing_nsg_name : azurerm_network_security_group.this[0].name

  depends_on = [
    azurerm_network_security_group.this
  ]
}
