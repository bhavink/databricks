# ==============================================
# Standalone Non-PL Azure Databricks Workspace
# ==============================================
# Self-contained: no modules, no CMK, no Private Link, no SEPs.
# Optional: attach to existing Unity Catalog metastore via existing_metastore_id.
# ==============================================

resource "random_string" "suffix" {
  length  = 4
  special = false
  upper   = false
  lower   = true
  numeric = true
}

# ----------------------------------------------
# Resource Group
# ----------------------------------------------
resource "azurerm_resource_group" "this" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

# ----------------------------------------------
# Virtual Network
# ----------------------------------------------
resource "azurerm_virtual_network" "this" {
  name                = "${var.workspace_prefix}-vnet-${random_string.suffix.result}"
  address_space       = var.vnet_address_space
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = var.tags
}

# ----------------------------------------------
# Subnets (Databricks delegation required)
# ----------------------------------------------
resource "azurerm_subnet" "public" {
  name                 = "${var.workspace_prefix}-public-${random_string.suffix.result}"
  resource_group_name  = azurerm_resource_group.this.name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = var.public_subnet_address_prefix

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
}

resource "azurerm_subnet" "private" {
  name                 = "${var.workspace_prefix}-private-${random_string.suffix.result}"
  resource_group_name  = azurerm_resource_group.this.name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = var.private_subnet_address_prefix

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
}

# ----------------------------------------------
# Network Security Group (empty; Databricks adds rules when public access is on)
# ----------------------------------------------
resource "azurerm_network_security_group" "this" {
  name                = "${var.workspace_prefix}-nsg-${random_string.suffix.result}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = var.tags
}

resource "azurerm_subnet_network_security_group_association" "public" {
  subnet_id                 = azurerm_subnet.public.id
  network_security_group_id = azurerm_network_security_group.this.id
}

resource "azurerm_subnet_network_security_group_association" "private" {
  subnet_id                 = azurerm_subnet.private.id
  network_security_group_id = azurerm_network_security_group.this.id
}

# ----------------------------------------------
# NAT Gateway (egress for clusters)
# ----------------------------------------------
resource "azurerm_public_ip" "nat" {
  name                = "${var.workspace_prefix}-nat-pip-${random_string.suffix.result}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = var.tags
}

resource "azurerm_nat_gateway" "this" {
  name                = "${var.workspace_prefix}-nat-${random_string.suffix.result}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  sku_name            = "Standard"
  tags                = var.tags
}

resource "azurerm_nat_gateway_public_ip_association" "this" {
  nat_gateway_id       = azurerm_nat_gateway.this.id
  public_ip_address_id = azurerm_public_ip.nat.id
}

resource "azurerm_subnet_nat_gateway_association" "public" {
  subnet_id      = azurerm_subnet.public.id
  nat_gateway_id = azurerm_nat_gateway.this.id
}

resource "azurerm_subnet_nat_gateway_association" "private" {
  subnet_id      = azurerm_subnet.private.id
  nat_gateway_id = azurerm_nat_gateway.this.id
}

# ----------------------------------------------
# Databricks Workspace (no CMK, no Private Link)
# ----------------------------------------------
resource "azurerm_databricks_workspace" "this" {
  name                        = "${var.workspace_prefix}-workspace-${random_string.suffix.result}"
  resource_group_name         = azurerm_resource_group.this.name
  location                    = azurerm_resource_group.this.location
  sku                         = "standard"
  managed_resource_group_name = "${var.workspace_prefix}-managed-rg-${random_string.suffix.result}"

  public_network_access_enabled         = true
  network_security_group_rules_required = "AllRules"
  customer_managed_key_enabled          = false

  custom_parameters {
    no_public_ip = true
    public_subnet_name  = azurerm_subnet.public.name
    private_subnet_name = azurerm_subnet.private.name
    virtual_network_id  = azurerm_virtual_network.this.id
    public_subnet_network_security_group_association_id  = azurerm_subnet_network_security_group_association.public.id
    private_subnet_network_security_group_association_id = azurerm_subnet_network_security_group_association.private.id
  }

  tags = var.tags
}

# ----------------------------------------------
# Attach workspace to existing Unity Catalog metastore (optional)
# ----------------------------------------------
resource "databricks_metastore_assignment" "this" {
  count = (var.existing_metastore_id != "" && var.databricks_host != "") ? 1 : 0

  workspace_id         = azurerm_databricks_workspace.this.workspace_id
  metastore_id         = var.existing_metastore_id
  default_catalog_name = var.default_catalog_name
}
