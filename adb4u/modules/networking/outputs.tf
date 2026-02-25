# ==============================================
# Essential Outputs (Simple Use)
# ==============================================

output "vnet_id" {
  description = "Virtual Network ID"
  value       = local.vnet_id
}

output "vnet_name" {
  description = "Virtual Network name"
  value       = local.vnet_name
}

output "subnet_ids" {
  description = "Subnet IDs for Databricks workspace"
  value = {
    public      = local.public_subnet_id
    private     = local.private_subnet_id
    privatelink = var.enable_private_link ? (var.use_existing_network && var.existing_privatelink_subnet_name != "" ? data.azurerm_subnet.existing_privatelink[0].id : azurerm_subnet.privatelink[0].id) : null
  }
}

output "subnet_names" {
  description = "Subnet names for Databricks workspace"
  value = {
    public      = local.public_subnet_name
    private     = local.private_subnet_name
    privatelink = var.enable_private_link ? (var.use_existing_network && var.existing_privatelink_subnet_name != "" ? var.existing_privatelink_subnet_name : azurerm_subnet.privatelink[0].name) : null
  }
}

output "nsg_id" {
  description = "Network Security Group ID"
  value       = local.nsg_id
}

output "nsg_name" {
  description = "Network Security Group name"
  value       = local.using_existing ? var.existing_nsg_name : azurerm_network_security_group.this[0].name
}

output "nat_gateway_id" {
  description = "NAT Gateway ID (null if not created)"
  value       = local.nat_gateway_id
}

output "nat_gateway_public_ip" {
  description = "NAT Gateway public IP address (null if not created)"
  value       = var.enable_nat_gateway ? azurerm_public_ip.nat[0].ip_address : null
}

# NSG Association IDs (required for workspace)
output "public_subnet_nsg_association_id" {
  description = "Public subnet NSG association ID"
  value       = local.using_existing ? var.existing_public_subnet_nsg_association_id : azurerm_subnet_network_security_group_association.public[0].id
}

output "private_subnet_nsg_association_id" {
  description = "Private subnet NSG association ID"
  value       = local.using_existing ? var.existing_private_subnet_nsg_association_id : azurerm_subnet_network_security_group_association.private[0].id
}

# ==============================================
# Documentation Outputs
# ==============================================

output "nsg_rules_added" {
  description = "List of NSG rules automatically added by this module (for documentation)"
  value = var.enable_private_link ? [
    "Inbound Priority 100: VirtualNetwork → VirtualNetwork (Any)",
    "Outbound Priority 100: VirtualNetwork → AzureDatabricks (443, 3306, 8443-8451)",
    "Outbound Priority 101: VirtualNetwork → Sql (3306)",
    "Outbound Priority 102: VirtualNetwork → Storage (443)",
    "Outbound Priority 103: VirtualNetwork → VirtualNetwork (Any)",
    "Outbound Priority 104: VirtualNetwork → EventHub (9093)",
    "Outbound Priority 105: VirtualNetwork → Internet (111, 2049) - for library installs",
    ] : [
    "NSG rules managed by Databricks (Non-PL mode)"
  ]
}

output "network_configuration" {
  description = "Summary of network configuration"
  value = {
    mode                    = var.use_existing_network ? "BYOV (Bring Your Own VNet)" : "Created"
    vnet_name               = local.vnet_name
    public_subnet_name      = local.public_subnet_name
    private_subnet_name     = local.private_subnet_name
    privatelink_subnet_name = var.enable_private_link ? (var.use_existing_network && var.existing_privatelink_subnet_name != "" ? var.existing_privatelink_subnet_name : azurerm_subnet.privatelink[0].name) : "Not configured"
    nsg_name                = local.using_existing ? var.existing_nsg_name : azurerm_network_security_group.this[0].name
    nat_gateway_enabled     = var.enable_nat_gateway
    nat_gateway_ip          = var.enable_nat_gateway ? azurerm_public_ip.nat[0].ip_address : "Not configured"
    private_link_enabled    = var.enable_private_link
    service_endpoints       = ["Microsoft.Storage", "Microsoft.KeyVault"]
  }
}

# ==============================================
# Advanced Outputs (Full Objects)
# ==============================================

output "vnet" {
  description = "Complete VNet object (for advanced use)"
  value       = local.vnet
}

output "subnets" {
  description = "Complete subnet objects (for advanced use)"
  value = {
    public      = local.public_subnet
    private     = local.private_subnet
    privatelink = var.enable_private_link ? (var.use_existing_network && var.existing_privatelink_subnet_name != "" ? data.azurerm_subnet.existing_privatelink[0] : azurerm_subnet.privatelink[0]) : null
  }
}

output "nsg" {
  description = "Complete NSG object (for advanced use)"
  value       = local.nsg
}
