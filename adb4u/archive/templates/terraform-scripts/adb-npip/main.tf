# variable "prefix" {}
# variable "adb_vnet_cidr" {}
# variable "adb_host_subnet" {}
# variable "adb_container_subnet" {}
# variable "tag_environment" {}
# variable "tag_pricing" {}
# variable "tag_owner" {}
# variable "tag_keepuntil" {}


resource "azurerm_resource_group" "adb_rg" {
  name     = "${var.prefix}-tf-dbx-npip-rg"
  location = "westus"
}

resource "azurerm_virtual_network" "adb_vnet" {
  name                = "${var.prefix}-tf-dbx-databricks-vnet"
  address_space       = var.adb_vnet_cidr
  location            = azurerm_resource_group.adb_rg.location
  resource_group_name = azurerm_resource_group.adb_rg.name
}

resource "azurerm_subnet" "public" {
  name                 = "${var.prefix}-tf-dbx-node-subnet"
  resource_group_name  = azurerm_resource_group.adb_rg.name
  virtual_network_name = azurerm_virtual_network.adb_vnet.name
  address_prefixes     = var.adb_host_subnet

  delegation {
    name = "${var.prefix}-databricks-del"

    service_delegation {
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
        "Microsoft.Network/virtualNetworks/subnets/prepareNetworkPolicies/action",
        "Microsoft.Network/virtualNetworks/subnets/unprepareNetworkPolicies/action",
      ]
      name = "Microsoft.Databricks/workspaces"
    }
  }
}

resource "azurerm_subnet" "private" {
  name                 = "${var.prefix}-tf-dbx-container-subnet"
  resource_group_name  = azurerm_resource_group.adb_rg.name
  virtual_network_name = azurerm_virtual_network.adb_vnet.name
  address_prefixes     = var.adb_container_subnet

  delegation {
    name = "${var.prefix}-databricks-del"

    service_delegation {
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
        "Microsoft.Network/virtualNetworks/subnets/prepareNetworkPolicies/action",
        "Microsoft.Network/virtualNetworks/subnets/unprepareNetworkPolicies/action",
      ]
      name = "Microsoft.Databricks/workspaces"
    }
  }
}

resource "azurerm_subnet_network_security_group_association" "private" {
  subnet_id                 = azurerm_subnet.private.id
  network_security_group_id = azurerm_network_security_group.adb_nsg.id
}

resource "azurerm_subnet_network_security_group_association" "public" {
  subnet_id                 = azurerm_subnet.public.id
  network_security_group_id = azurerm_network_security_group.adb_nsg.id
}

resource "azurerm_network_security_group" "adb_nsg" {
  name                = "${var.prefix}-tf-dbx-databricks-nsg"
  location            = azurerm_resource_group.adb_rg.location
  resource_group_name = azurerm_resource_group.adb_rg.name
}

resource "azurerm_databricks_workspace" "adb_ws" {
  name                        = "DBW-${var.prefix}"
  resource_group_name         = azurerm_resource_group.adb_rg.name
  location                    = azurerm_resource_group.adb_rg.location
  sku                         = "premium"
  managed_resource_group_name = "${var.prefix}-tf-dbx-DBW-managed-rg"

  public_network_access_enabled = true

  custom_parameters {
    no_public_ip        = true
    public_subnet_name  = azurerm_subnet.public.name
    private_subnet_name = azurerm_subnet.private.name
    virtual_network_id  = azurerm_virtual_network.adb_vnet.id

    public_subnet_network_security_group_association_id  = azurerm_subnet_network_security_group_association.public.id
    private_subnet_network_security_group_association_id = azurerm_subnet_network_security_group_association.private.id
  }

  tags = {
    Environment = var.tag_environment
    Pricing     = var.tag_pricing
    Owner       = var.tag_owner
    KeepUntil   = var.tag_keepuntil
  }
}