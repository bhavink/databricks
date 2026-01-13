***REMOVED*** ==============================================
***REMOVED*** BYOR (Bring Your Own Resources) Deployment
***REMOVED*** ==============================================
***REMOVED***
***REMOVED*** This deployment creates Databricks-ready infrastructure that can be
***REMOVED*** reused across multiple workspace deployments (Non-PL, Full-Private).
***REMOVED***
***REMOVED*** Resources Created:
***REMOVED*** - VNet with Databricks subnets (with delegation)
***REMOVED*** - NSG with Databricks-required rules
***REMOVED*** - Service Endpoints (Storage, KeyVault, EventHub)
***REMOVED*** - (Optional) NAT Gateway for Non-PL pattern
***REMOVED*** - (Optional) Private Link subnet for Full-Private pattern
***REMOVED*** - (Optional) Key Vault + CMK for encryption
***REMOVED***
***REMOVED*** Output: Copy-paste ready configuration for workspace deployment
***REMOVED***
***REMOVED*** ==============================================

***REMOVED*** Random suffix for unique resource naming
resource "random_string" "deployment_suffix" {
  length  = 4
  special = false
  upper   = false
  lower   = true
  numeric = true
}

locals {
  ***REMOVED*** Merge user-provided tags with required owner and keepuntil tags
  all_tags = merge(
    var.tags,
    {
      Owner     = var.tag_owner
      KeepUntil = var.tag_keepuntil
    }
  )
}

***REMOVED*** ==============================================
***REMOVED*** Resource Group
***REMOVED*** ==============================================

data "azurerm_resource_group" "existing" {
  count = var.use_existing_resource_group ? 1 : 0
  name  = var.resource_group_name
}

resource "azurerm_resource_group" "this" {
  count    = var.use_existing_resource_group ? 0 : 1
  name     = var.resource_group_name
  location = var.location
  tags     = local.all_tags
}

locals {
  resource_group_name = var.use_existing_resource_group ? data.azurerm_resource_group.existing[0].name : azurerm_resource_group.this[0].name
  resource_group_id   = var.use_existing_resource_group ? data.azurerm_resource_group.existing[0].id : azurerm_resource_group.this[0].id
}

***REMOVED*** ==============================================
***REMOVED*** Virtual Network
***REMOVED*** ==============================================

resource "azurerm_virtual_network" "this" {
  name                = "${var.workspace_prefix}-vnet-${random_string.deployment_suffix.result}"
  location            = var.location
  resource_group_name = local.resource_group_name
  address_space       = var.vnet_address_space
  tags                = local.all_tags

  depends_on = [
    azurerm_resource_group.this
  ]
}

***REMOVED*** ==============================================
***REMOVED*** Network Security Group (NSG)
***REMOVED*** ==============================================

resource "azurerm_network_security_group" "this" {
  name                = "${var.workspace_prefix}-nsg-${random_string.deployment_suffix.result}"
  location            = var.location
  resource_group_name = local.resource_group_name
  tags                = local.all_tags

  ***REMOVED*** Databricks-required rules for NPIP (Secure Cluster Connectivity)
  ***REMOVED*** Reference: https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/customer-managed-vpc
  
  security_rule {
    name                       = "AllowAzureDatabricksControlPlane"
    priority                   = 200
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "AzureDatabricks"
    description                = "Required for cluster communication with Databricks control plane"
  }

  security_rule {
    name                       = "AllowAzureStorage"
    priority                   = 201
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "Storage"
    description                = "Required for DBFS and artifact storage access"
  }

  security_rule {
    name                       = "AllowAzureEventHub"
    priority                   = 202
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "EventHub"
    description                = "Required for log delivery and metrics"
  }

  security_rule {
    name                       = "AllowWorkerToWorker"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "VirtualNetwork"
    description                = "Required for worker-to-worker communication within the VNet"
  }

  depends_on = [azurerm_virtual_network.this]
}

***REMOVED*** ==============================================
***REMOVED*** Public/Host Subnet
***REMOVED*** ==============================================

resource "azurerm_subnet" "public" {
  name                 = "${var.workspace_prefix}-public-subnet-${random_string.deployment_suffix.result}"
  resource_group_name  = local.resource_group_name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = [var.public_subnet_address_prefix]

  ***REMOVED*** Subnet delegation for Databricks
  delegation {
    name = "databricks-delegation"

    service_delegation {
      name = "Microsoft.Databricks/workspaces"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
        "Microsoft.Network/virtualNetworks/subnets/prepareNetworkPolicies/action",
        "Microsoft.Network/virtualNetworks/subnets/unprepareNetworkPolicies/action"
      ]
    }
  }

  ***REMOVED*** Service Endpoints
  service_endpoints = [
    "Microsoft.Storage",
    "Microsoft.KeyVault",
    "Microsoft.EventHub"
  ]

  depends_on = [azurerm_virtual_network.this]
}

resource "azurerm_subnet_network_security_group_association" "public" {
  subnet_id                 = azurerm_subnet.public.id
  network_security_group_id = azurerm_network_security_group.this.id

  depends_on = [
    azurerm_subnet.public,
    azurerm_network_security_group.this
  ]
}

***REMOVED*** ==============================================
***REMOVED*** Private/Container Subnet
***REMOVED*** ==============================================

resource "azurerm_subnet" "private" {
  name                 = "${var.workspace_prefix}-private-subnet-${random_string.deployment_suffix.result}"
  resource_group_name  = local.resource_group_name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = [var.private_subnet_address_prefix]

  ***REMOVED*** Subnet delegation for Databricks
  delegation {
    name = "databricks-delegation"

    service_delegation {
      name = "Microsoft.Databricks/workspaces"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
        "Microsoft.Network/virtualNetworks/subnets/prepareNetworkPolicies/action",
        "Microsoft.Network/virtualNetworks/subnets/unprepareNetworkPolicies/action"
      ]
    }
  }

  ***REMOVED*** Service Endpoints
  service_endpoints = [
    "Microsoft.Storage",
    "Microsoft.KeyVault",
    "Microsoft.EventHub"
  ]

  depends_on = [azurerm_virtual_network.this]
}

resource "azurerm_subnet_network_security_group_association" "private" {
  subnet_id                 = azurerm_subnet.private.id
  network_security_group_id = azurerm_network_security_group.this.id

  depends_on = [
    azurerm_subnet.private,
    azurerm_network_security_group.this
  ]
}

***REMOVED*** ==============================================
***REMOVED*** Private Link Subnet (Optional - for Full-Private)
***REMOVED*** ==============================================

resource "azurerm_subnet" "privatelink" {
  count                = var.create_privatelink_subnet ? 1 : 0
  name                 = "${var.workspace_prefix}-privatelink-subnet-${random_string.deployment_suffix.result}"
  resource_group_name  = local.resource_group_name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = [var.privatelink_subnet_address_prefix]

  ***REMOVED*** NO delegation - Private Link subnets cannot have delegation
  ***REMOVED*** Private Endpoints are not compatible with subnet delegation
  ***REMOVED*** Reference: https://learn.microsoft.com/en-us/azure/private-link/private-endpoint-overview***REMOVED***private-endpoint-properties

  ***REMOVED*** Service Endpoints (for hybrid scenarios)
  service_endpoints = [
    "Microsoft.Storage",
    "Microsoft.KeyVault"
  ]

  depends_on = [azurerm_virtual_network.this]
}

***REMOVED*** ==============================================
***REMOVED*** NAT Gateway (Optional - for Non-PL)
***REMOVED*** ==============================================

resource "azurerm_public_ip" "nat" {
  count               = var.enable_nat_gateway ? 1 : 0
  name                = "${var.workspace_prefix}-nat-pip-${random_string.deployment_suffix.result}"
  location            = var.location
  resource_group_name = local.resource_group_name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = local.all_tags

  depends_on = [
    azurerm_resource_group.this
  ]
}

resource "azurerm_nat_gateway" "this" {
  count               = var.enable_nat_gateway ? 1 : 0
  name                = "${var.workspace_prefix}-nat-${random_string.deployment_suffix.result}"
  location            = var.location
  resource_group_name = local.resource_group_name
  sku_name            = "Standard"
  tags                = local.all_tags

  depends_on = [
    azurerm_resource_group.this
  ]
}

resource "azurerm_nat_gateway_public_ip_association" "this" {
  count                = var.enable_nat_gateway ? 1 : 0
  nat_gateway_id       = azurerm_nat_gateway.this[0].id
  public_ip_address_id = azurerm_public_ip.nat[0].id

  depends_on = [
    azurerm_nat_gateway.this,
    azurerm_public_ip.nat
  ]
}

resource "azurerm_subnet_nat_gateway_association" "public" {
  count          = var.enable_nat_gateway ? 1 : 0
  subnet_id      = azurerm_subnet.public.id
  nat_gateway_id = azurerm_nat_gateway.this[0].id

  depends_on = [
    azurerm_subnet.public,
    azurerm_nat_gateway.this,
    azurerm_subnet_network_security_group_association.public
  ]
}

resource "azurerm_subnet_nat_gateway_association" "private" {
  count          = var.enable_nat_gateway ? 1 : 0
  subnet_id      = azurerm_subnet.private.id
  nat_gateway_id = azurerm_nat_gateway.this[0].id

  depends_on = [
    azurerm_subnet.private,
    azurerm_nat_gateway.this,
    azurerm_subnet_network_security_group_association.private
  ]
}

***REMOVED*** ==============================================
***REMOVED*** Key Vault Module (Optional - for CMK)
***REMOVED*** ==============================================

module "key_vault" {
  count  = var.create_key_vault ? 1 : 0
  source = "../../modules/key-vault"

  create_key_vault       = true
  key_name               = "databricks-cmk-${random_string.deployment_suffix.result}"
  key_type               = var.cmk_key_type
  key_size               = var.cmk_key_size
  resource_group_name    = local.resource_group_name
  location               = var.location
  workspace_prefix       = var.workspace_prefix
  tags                   = local.all_tags
  databricks_principal_id = "" ***REMOVED*** Will be set by workspace team during deployment

  depends_on = [
    azurerm_resource_group.this
  ]
}
