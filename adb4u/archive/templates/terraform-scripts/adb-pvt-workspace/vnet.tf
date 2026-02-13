# Azure Virtual Network resource defining the main network for the deployment.
# Uses a unique prefix and address space from local variables.
resource "azurerm_virtual_network" "this" {
  name                = "${local.prefix}-vnet"  # VNet name with unique prefix
  location            = azurerm_resource_group.this.location  # Region of the resource group
  resource_group_name = azurerm_resource_group.this.name  # Resource group for the VNet
  address_space       = [local.cidr]  # IP address range for the VNet
  tags                = local.tags  # Tags for resource identification and management
}

# Network Security Group (NSG) resource for managing traffic rules.
# Will be associated with public and private subnets.
resource "azurerm_network_security_group" "this" {
  name                = "${local.prefix}-nsg"  # NSG name with unique prefix
  location            = azurerm_resource_group.this.location  # Region of the NSG
  resource_group_name = azurerm_resource_group.this.name  # Resource group for the NSG
  tags                = local.tags  # Tags for resource identification
}

# Public Subnet within the VNet, dedicated for Databricks workspace access.
# Address prefix is derived using CIDR notation.
resource "azurerm_subnet" "public" {
  name                 = "${local.prefix}-public"  # Subnet name with unique prefix
  resource_group_name  = azurerm_resource_group.this.name  # Resource group for the subnet
  virtual_network_name = azurerm_virtual_network.this.name  # Parent VNet for the subnet
  address_prefixes     = [cidrsubnet(local.cidr, 3, 0)]  # IP address range for the public subnet

  # Delegates subnet to Databricks service, allowing Databricks to manage network policies.
  delegation {
    name = "databricks"
    service_delegation {
      name = "Microsoft.Databricks/workspaces"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",  # Allows Databricks workspace join
        "Microsoft.Network/virtualNetworks/subnets/prepareNetworkPolicies/action",  # Prepares network policies
        "Microsoft.Network/virtualNetworks/subnets/unprepareNetworkPolicies/action"  # Unprepares policies if needed
      ]
    }
  }
}

# Associates the Network Security Group with the public subnet to apply security rules.
resource "azurerm_subnet_network_security_group_association" "public" {
  subnet_id                 = azurerm_subnet.public.id  # Public subnet ID
  network_security_group_id = azurerm_network_security_group.this.id  # NSG ID to associate
}

# List of private subnet service endpoints, defaults to empty.
variable "private_subnet_endpoints" {
  default = []
}

# Private Subnet within the VNet, dedicated to Databricks secure operations.
# Configured with delegated access for Databricks services and optional service endpoints.
resource "azurerm_subnet" "private" {
  name                 = "${local.prefix}-private"  # Private subnet name with unique prefix
  resource_group_name  = azurerm_resource_group.this.name  # Resource group for the subnet
  virtual_network_name = azurerm_virtual_network.this.name  # Parent VNet for the subnet
  address_prefixes     = [cidrsubnet(local.cidr, 3, 1)]  # IP address range for the private subnet

  # Delegates subnet to Databricks, allowing service management of network policies.
  delegation {
    name = "databricks"
    service_delegation {
      name = "Microsoft.Databricks/workspaces"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",  # Allows Databricks workspace join
        "Microsoft.Network/virtualNetworks/subnets/prepareNetworkPolicies/action",  # Prepares network policies
        "Microsoft.Network/virtualNetworks/subnets/unprepareNetworkPolicies/action"  # Unprepares policies if needed
      ]
    }
  }

  service_endpoints = var.private_subnet_endpoints  # Optional private subnet endpoints
}

# Associates the Network Security Group with the private subnet to enforce security rules.
resource "azurerm_subnet_network_security_group_association" "private" {
  subnet_id                 = azurerm_subnet.private.id  # Private subnet ID
  network_security_group_id = azurerm_network_security_group.this.id  # NSG ID to associate
}

# Private Link Subnet, reserved for private link connections within the Databricks VNet.
# Assigned a unique address prefix and used for securing private endpoints.
resource "azurerm_subnet" "plsubnet" {
  name                                           = "${local.prefix}-privatelink"  # Name with unique prefix
  resource_group_name                            = azurerm_resource_group.this.name  # Resource group for the subnet
  virtual_network_name                           = azurerm_virtual_network.this.name  # Parent VNet for the subnet
  address_prefixes                               = [cidrsubnet(local.cidr, 3, 2)]  # IP range for the private link subnet
}
