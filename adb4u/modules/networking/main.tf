***REMOVED*** ==============================================
***REMOVED*** Data Sources (Existing Network Resources)
***REMOVED*** ==============================================

data "azurerm_virtual_network" "existing" {
  count               = var.use_existing_network ? 1 : 0
  name                = var.existing_vnet_name
  resource_group_name = var.existing_resource_group_name
}

data "azurerm_subnet" "existing_public" {
  count                = var.use_existing_network ? 1 : 0
  name                 = var.existing_public_subnet_name
  virtual_network_name = var.existing_vnet_name
  resource_group_name  = var.existing_resource_group_name
}

data "azurerm_subnet" "existing_private" {
  count                = var.use_existing_network ? 1 : 0
  name                 = var.existing_private_subnet_name
  virtual_network_name = var.existing_vnet_name
  resource_group_name  = var.existing_resource_group_name
}

data "azurerm_network_security_group" "existing" {
  count               = var.use_existing_network ? 1 : 0
  name                = var.existing_nsg_name
  resource_group_name = var.existing_resource_group_name
}

***REMOVED*** ==============================================
***REMOVED*** Virtual Network (Created New)
***REMOVED*** ==============================================

resource "azurerm_virtual_network" "this" {
  count               = var.use_existing_network ? 0 : 1
  name                = local.vnet_name_new
  address_space       = var.vnet_address_space
  location            = var.location
  resource_group_name = var.resource_group_name

  tags = var.tags
}

***REMOVED*** ==============================================
***REMOVED*** Subnets with Databricks Delegation
***REMOVED*** ==============================================

resource "azurerm_subnet" "public" {
  count                = var.use_existing_network ? 0 : 1
  name                 = "${var.workspace_prefix}-public-subnet-${random_string.suffix.result}"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.this[0].name
  address_prefixes     = var.public_subnet_address_prefix

  ***REMOVED*** Databricks delegation (REQUIRED)
  delegation {
    name = "databricks-delegation"

    service_delegation {
      name = "Microsoft.Databricks/workspaces"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
        "Microsoft.Network/virtualNetworks/subnets/prepareNetworkPolicies/action",
        "Microsoft.Network/virtualNetworks/subnets/unprepareNetworkPolicies/action",
      ]
    }
  }

  ***REMOVED*** Service Endpoints for Unity Catalog storage
  service_endpoints = [
    "Microsoft.Storage",
    "Microsoft.KeyVault",
  ]
  
  ***REMOVED*** Service Endpoint Policy IDs (optional - for storage egress control)
  service_endpoint_policy_ids = var.service_endpoint_policy_ids
}

resource "azurerm_subnet" "private" {
  count                = var.use_existing_network ? 0 : 1
  name                 = "${var.workspace_prefix}-private-subnet-${random_string.suffix.result}"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.this[0].name
  address_prefixes     = var.private_subnet_address_prefix

  ***REMOVED*** Databricks delegation (REQUIRED)
  delegation {
    name = "databricks-delegation"

    service_delegation {
      name = "Microsoft.Databricks/workspaces"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
        "Microsoft.Network/virtualNetworks/subnets/prepareNetworkPolicies/action",
        "Microsoft.Network/virtualNetworks/subnets/unprepareNetworkPolicies/action",
      ]
    }
  }

  ***REMOVED*** Service Endpoints for Unity Catalog storage
  service_endpoints = [
    "Microsoft.Storage",
    "Microsoft.KeyVault",
  ]
  
  ***REMOVED*** Service Endpoint Policy IDs (optional - for storage egress control)
  service_endpoint_policy_ids = var.service_endpoint_policy_ids
}

***REMOVED*** ==============================================
***REMOVED*** Private Link Subnet (Full Private Pattern Only)
***REMOVED*** ==============================================

resource "azurerm_subnet" "privatelink" {
  count                = var.enable_private_link && !var.use_existing_network ? 1 : 0
  name                 = "${var.workspace_prefix}-privatelink-subnet-${random_string.suffix.result}"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.this[0].name
  address_prefixes     = var.privatelink_subnet_address_prefix

  ***REMOVED*** NO Databricks delegation for Private Link subnet
  ***REMOVED*** NO NAT Gateway for Private Link subnet (air-gapped)
  ***REMOVED*** NO Service Endpoints (using Private Link for storage)
}

***REMOVED*** Existing Private Link Subnet (BYOV)
data "azurerm_subnet" "existing_privatelink" {
  count                = var.use_existing_network && var.enable_private_link && var.existing_privatelink_subnet_name != "" ? 1 : 0
  name                 = var.existing_privatelink_subnet_name
  virtual_network_name = var.existing_vnet_name
  resource_group_name  = var.existing_resource_group_name
}

***REMOVED*** ==============================================
***REMOVED*** Network Security Group
***REMOVED*** ==============================================

resource "azurerm_network_security_group" "this" {
  count               = var.use_existing_network ? 0 : 1
  name                = local.nsg_name_new
  location            = var.location
  resource_group_name = var.resource_group_name

  tags = var.tags
}

***REMOVED*** Associate NSG with Public Subnet
resource "azurerm_subnet_network_security_group_association" "public" {
  count                     = var.use_existing_network ? 0 : 1
  subnet_id                 = azurerm_subnet.public[0].id
  network_security_group_id = azurerm_network_security_group.this[0].id
}

***REMOVED*** Associate NSG with Private Subnet
resource "azurerm_subnet_network_security_group_association" "private" {
  count                     = var.use_existing_network ? 0 : 1
  subnet_id                 = azurerm_subnet.private[0].id
  network_security_group_id = azurerm_network_security_group.this[0].id
}

***REMOVED*** ==============================================
***REMOVED*** NAT Gateway for Stable Egress IP
***REMOVED*** ==============================================

resource "azurerm_public_ip" "nat" {
  count               = var.enable_nat_gateway ? 1 : 0
  name                = local.nat_pip_name
  location            = var.location
  resource_group_name = var.resource_group_name
  allocation_method   = "Static"
  sku                 = "Standard"

  tags = var.tags
}

resource "azurerm_nat_gateway" "this" {
  count               = var.enable_nat_gateway ? 1 : 0
  name                = local.nat_gateway_name
  location            = var.location
  resource_group_name = var.resource_group_name
  sku_name            = "Standard"

  tags = var.tags
}

resource "azurerm_nat_gateway_public_ip_association" "this" {
  count                = var.enable_nat_gateway ? 1 : 0
  nat_gateway_id       = azurerm_nat_gateway.this[0].id
  public_ip_address_id = azurerm_public_ip.nat[0].id
}

***REMOVED*** Associate NAT Gateway with Public Subnet
resource "azurerm_subnet_nat_gateway_association" "public" {
  count          = var.enable_nat_gateway && !var.use_existing_network ? 1 : 0
  subnet_id      = azurerm_subnet.public[0].id
  nat_gateway_id = azurerm_nat_gateway.this[0].id
}

***REMOVED*** Associate NAT Gateway with Private Subnet
resource "azurerm_subnet_nat_gateway_association" "private" {
  count          = var.enable_nat_gateway && !var.use_existing_network ? 1 : 0
  subnet_id      = azurerm_subnet.private[0].id
  nat_gateway_id = azurerm_nat_gateway.this[0].id
}

***REMOVED*** ==============================================
***REMOVED*** Subnet Delegation for Existing Subnets
***REMOVED*** ==============================================

***REMOVED*** Ensure Databricks delegation exists on user-provided subnets
***REMOVED*** Note: This is a protective measure. Azure will return error if delegation is missing.
***REMOVED*** Terraform cannot directly add delegation to existing subnets via azurerm_subnet resource,
***REMOVED*** so this must be validated via data source or handled by user.
***REMOVED*** 
***REMOVED*** IMPORTANT: User MUST ensure existing subnets have Microsoft.Databricks/workspaces delegation.
***REMOVED*** See README for instructions on adding delegation to existing subnets.
