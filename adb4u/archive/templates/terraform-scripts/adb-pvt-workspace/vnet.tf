***REMOVED*** Azure Virtual Network resource defining the main network for the deployment.
***REMOVED*** Uses a unique prefix and address space from local variables.
resource "azurerm_virtual_network" "this" {
  name                = "${local.prefix}-vnet"  ***REMOVED*** VNet name with unique prefix
  location            = azurerm_resource_group.this.location  ***REMOVED*** Region of the resource group
  resource_group_name = azurerm_resource_group.this.name  ***REMOVED*** Resource group for the VNet
  address_space       = [local.cidr]  ***REMOVED*** IP address range for the VNet
  tags                = local.tags  ***REMOVED*** Tags for resource identification and management
}

***REMOVED*** Network Security Group (NSG) resource for managing traffic rules.
***REMOVED*** Will be associated with public and private subnets.
resource "azurerm_network_security_group" "this" {
  name                = "${local.prefix}-nsg"  ***REMOVED*** NSG name with unique prefix
  location            = azurerm_resource_group.this.location  ***REMOVED*** Region of the NSG
  resource_group_name = azurerm_resource_group.this.name  ***REMOVED*** Resource group for the NSG
  tags                = local.tags  ***REMOVED*** Tags for resource identification
}

***REMOVED*** Public Subnet within the VNet, dedicated for Databricks workspace access.
***REMOVED*** Address prefix is derived using CIDR notation.
resource "azurerm_subnet" "public" {
  name                 = "${local.prefix}-public"  ***REMOVED*** Subnet name with unique prefix
  resource_group_name  = azurerm_resource_group.this.name  ***REMOVED*** Resource group for the subnet
  virtual_network_name = azurerm_virtual_network.this.name  ***REMOVED*** Parent VNet for the subnet
  address_prefixes     = [cidrsubnet(local.cidr, 3, 0)]  ***REMOVED*** IP address range for the public subnet

  ***REMOVED*** Delegates subnet to Databricks service, allowing Databricks to manage network policies.
  delegation {
    name = "databricks"
    service_delegation {
      name = "Microsoft.Databricks/workspaces"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",  ***REMOVED*** Allows Databricks workspace join
        "Microsoft.Network/virtualNetworks/subnets/prepareNetworkPolicies/action",  ***REMOVED*** Prepares network policies
        "Microsoft.Network/virtualNetworks/subnets/unprepareNetworkPolicies/action"  ***REMOVED*** Unprepares policies if needed
      ]
    }
  }
}

***REMOVED*** Associates the Network Security Group with the public subnet to apply security rules.
resource "azurerm_subnet_network_security_group_association" "public" {
  subnet_id                 = azurerm_subnet.public.id  ***REMOVED*** Public subnet ID
  network_security_group_id = azurerm_network_security_group.this.id  ***REMOVED*** NSG ID to associate
}

***REMOVED*** List of private subnet service endpoints, defaults to empty.
variable "private_subnet_endpoints" {
  default = []
}

***REMOVED*** Private Subnet within the VNet, dedicated to Databricks secure operations.
***REMOVED*** Configured with delegated access for Databricks services and optional service endpoints.
resource "azurerm_subnet" "private" {
  name                 = "${local.prefix}-private"  ***REMOVED*** Private subnet name with unique prefix
  resource_group_name  = azurerm_resource_group.this.name  ***REMOVED*** Resource group for the subnet
  virtual_network_name = azurerm_virtual_network.this.name  ***REMOVED*** Parent VNet for the subnet
  address_prefixes     = [cidrsubnet(local.cidr, 3, 1)]  ***REMOVED*** IP address range for the private subnet

  ***REMOVED*** Delegates subnet to Databricks, allowing service management of network policies.
  delegation {
    name = "databricks"
    service_delegation {
      name = "Microsoft.Databricks/workspaces"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",  ***REMOVED*** Allows Databricks workspace join
        "Microsoft.Network/virtualNetworks/subnets/prepareNetworkPolicies/action",  ***REMOVED*** Prepares network policies
        "Microsoft.Network/virtualNetworks/subnets/unprepareNetworkPolicies/action"  ***REMOVED*** Unprepares policies if needed
      ]
    }
  }

  service_endpoints = var.private_subnet_endpoints  ***REMOVED*** Optional private subnet endpoints
}

***REMOVED*** Associates the Network Security Group with the private subnet to enforce security rules.
resource "azurerm_subnet_network_security_group_association" "private" {
  subnet_id                 = azurerm_subnet.private.id  ***REMOVED*** Private subnet ID
  network_security_group_id = azurerm_network_security_group.this.id  ***REMOVED*** NSG ID to associate
}

***REMOVED*** Private Link Subnet, reserved for private link connections within the Databricks VNet.
***REMOVED*** Assigned a unique address prefix and used for securing private endpoints.
resource "azurerm_subnet" "plsubnet" {
  name                                           = "${local.prefix}-privatelink"  ***REMOVED*** Name with unique prefix
  resource_group_name                            = azurerm_resource_group.this.name  ***REMOVED*** Resource group for the subnet
  virtual_network_name                           = azurerm_virtual_network.this.name  ***REMOVED*** Parent VNet for the subnet
  address_prefixes                               = [cidrsubnet(local.cidr, 3, 2)]  ***REMOVED*** IP range for the private link subnet
}
