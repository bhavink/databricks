***REMOVED*** Random suffix for unique resource names
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

***REMOVED*** ==============================================
***REMOVED*** Local Values
***REMOVED*** ==============================================

locals {
  ***REMOVED*** Determine if we're using existing or creating new
  using_existing = var.use_existing_network

  ***REMOVED*** VNet references
  vnet = local.using_existing ? data.azurerm_virtual_network.existing[0] : azurerm_virtual_network.this[0]
  vnet_id   = local.vnet.id
  vnet_name = local.vnet.name

  ***REMOVED*** Subnet references
  public_subnet = local.using_existing ? data.azurerm_subnet.existing_public[0] : azurerm_subnet.public[0]
  public_subnet_id   = local.public_subnet.id
  public_subnet_name = local.public_subnet.name

  private_subnet = local.using_existing ? data.azurerm_subnet.existing_private[0] : azurerm_subnet.private[0]
  private_subnet_id   = local.private_subnet.id
  private_subnet_name = local.private_subnet.name

  ***REMOVED*** NSG references
  nsg    = local.using_existing ? data.azurerm_network_security_group.existing[0] : azurerm_network_security_group.this[0]
  nsg_id = local.nsg.id

  ***REMOVED*** NAT Gateway reference
  nat_gateway_id = var.enable_nat_gateway ? azurerm_nat_gateway.this[0].id : null

  ***REMOVED*** Resource naming
  vnet_name_new    = "${var.workspace_prefix}-vnet-${random_string.suffix.result}"
  nsg_name_new     = "${var.workspace_prefix}-nsg-${random_string.suffix.result}"
  nat_gateway_name = "${var.workspace_prefix}-nat-${random_string.suffix.result}"
  nat_pip_name     = "${var.workspace_prefix}-nat-pip-${random_string.suffix.result}"
}
