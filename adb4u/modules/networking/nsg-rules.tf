# ==============================================
# NSG Rules for Secure Cluster Connectivity (SCC/NPIP)
# ==============================================
#
# Reference: https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/vnet-inject#network-security-group-rules-for-workspaces
#
# IMPORTANT: NSG rules are only created when BOTH conditions are met:
# 1. Private Link is enabled (enable_private_link = true)
# 2. Public network access is disabled (enable_public_network_access = false)
#
# Why? When public network access is enabled, Azure Databricks automatically creates 
# these rules (with "Microsoft.Databricks-workspaces_UseOnly_" prefix). We must NOT
# create duplicate rules as they will conflict.
#
# When fully locked down (Private Link + no public access), Databricks doesn't auto-create
# rules, so we must create them explicitly.
#
# NOTE: When SCC/NPIP is enabled, inbound rules on ports 22 and 5557 from 
# AzureDatabricks service tag are NOT required (and would be security risk).
#
# ==============================================

# Get the NSG ID (works for both new and existing)
locals {
  nsg_id_for_rules = local.nsg_id

  # Only create custom NSG rules when workspace is fully locked down
  create_custom_nsg_rules = var.enable_private_link && !var.enable_public_network_access
}

# ==============================================
# Inbound Rules
# ==============================================

# Allow inbound from VirtualNetwork to VirtualNetwork (Any protocol/port)
# This enables internal cluster communication
# Only create for Private Link deployments
resource "azurerm_network_security_rule" "inbound_vnet_to_vnet" {
  count = local.create_custom_nsg_rules ? 1 : 0

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

# ==============================================
# Outbound Rules
# ==============================================

# Allow outbound to AzureDatabricks service tag
# Required ports: 443 (HTTPS), 3306 (MySQL), 8443-8451 (internal)
# Only create for Private Link deployments
resource "azurerm_network_security_rule" "outbound_to_databricks" {
  count = local.create_custom_nsg_rules ? 1 : 0

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

# Allow outbound to SQL service tag (port 3306)
# Required for metadata operations
# Only create for Private Link deployments
resource "azurerm_network_security_rule" "outbound_to_sql" {
  count = local.create_custom_nsg_rules ? 1 : 0

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

# Allow outbound to Storage service tag (port 443)
# Required for Unity Catalog and workspace storage
# Only create for Private Link deployments
resource "azurerm_network_security_rule" "outbound_to_storage" {
  count = local.create_custom_nsg_rules ? 1 : 0

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

# Allow outbound within VirtualNetwork (Any protocol/port)
# Required for internal cluster communication
# Only create for Private Link deployments
resource "azurerm_network_security_rule" "outbound_vnet_to_vnet" {
  count = local.create_custom_nsg_rules ? 1 : 0

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

# Allow outbound to EventHub service tag (port 9093)
# Required for log delivery and diagnostics
# Only create for Private Link deployments
resource "azurerm_network_security_rule" "outbound_to_eventhub" {
  count = local.create_custom_nsg_rules ? 1 : 0

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

# Optional: Allow outbound for library installs (ports 111, 2049)
# Recommended by Databricks to enable certain library installations
# Only create for Private Link deployments
resource "azurerm_network_security_rule" "outbound_for_library_installs" {
  count = local.create_custom_nsg_rules ? 1 : 0

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
