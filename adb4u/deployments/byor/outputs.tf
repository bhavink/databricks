# ==============================================
# BYOR Outputs - Copy-Paste Ready for Workspace Deployment
# ==============================================

# ==============================================
# Copy-Paste Configuration Block
# ==============================================

output "copy_paste_config" {
  description = "Copy-paste this entire block into your workspace deployment terraform.tfvars"
  value = <<-EOT
# ==============================================
# BYOR Configuration (from BYOR deployment)
# Copy-paste this section into deployments/non-pl/terraform.tfvars
# or deployments/full-private/terraform.tfvars
# ==============================================

# Master Control - Use BYOR infrastructure
use_byor_infrastructure = true

# Core Configuration - MUST match BYOR deployment
location            = "${var.location}"
resource_group_name = "${local.resource_group_name}"

# Network Configuration (from BYOR)
existing_vnet_name            = "${azurerm_virtual_network.this.name}"
existing_resource_group_name  = "${local.resource_group_name}"
existing_public_subnet_name   = "${azurerm_subnet.public.name}"
existing_private_subnet_name  = "${azurerm_subnet.private.name}"
existing_nsg_name             = "${azurerm_network_security_group.this.name}"
${var.create_privatelink_subnet ? "existing_privatelink_subnet_name = \"${azurerm_subnet.privatelink[0].name}\"" : "# existing_privatelink_subnet_name = \"\"  # Not created (Full-Private only)"}

# NSG Association IDs (required for workspace deployment)
existing_public_subnet_nsg_association_id  = "${azurerm_subnet_network_security_group_association.public.id}"
existing_private_subnet_nsg_association_id = "${azurerm_subnet_network_security_group_association.private.id}"

${var.create_key_vault ? "# ==============================================\n# CMK Configuration (from BYOR deployment)\n# ==============================================\n\nenable_cmk_managed_services = true\nenable_cmk_managed_disks    = true\nenable_cmk_dbfs_root        = true\n\n# Key Vault from BYOR\nexisting_key_vault_id = \"${module.key_vault[0].key_vault_id}\"\nexisting_key_id       = \"${module.key_vault[0].key_id}\"" : "# ==============================================\n# CMK Configuration\n# Key Vault not created (set create_key_vault=true in BYOR to enable)\n# =============================================="}

# ==============================================
# Info: What BYOR Created
# ==============================================
${var.enable_nat_gateway ? "# ✅ NAT Gateway: Created (Public IP = ${azurerm_public_ip.nat[0].ip_address})" : "# ⚠️  NAT Gateway: Not created (enable_nat_gateway=false)"}
# ✅ Service Endpoints: Enabled (Storage, KeyVault, EventHub)
# ✅ Subnet Delegation: Applied (Microsoft.Databricks/workspaces)

EOT
}

# ==============================================
# Individual Outputs (for programmatic access)
# ==============================================

output "resource_group_name" {
  description = "Name of the resource group"
  value       = local.resource_group_name
}

output "resource_group_id" {
  description = "Resource ID of the resource group"
  value       = local.resource_group_id
}

output "vnet_name" {
  description = "Name of the Virtual Network"
  value       = azurerm_virtual_network.this.name
}

output "vnet_id" {
  description = "Resource ID of the Virtual Network"
  value       = azurerm_virtual_network.this.id
}

output "vnet_address_space" {
  description = "Address space of the Virtual Network"
  value       = azurerm_virtual_network.this.address_space
}

output "public_subnet_name" {
  description = "Name of the public/host subnet"
  value       = azurerm_subnet.public.name
}

output "public_subnet_id" {
  description = "Resource ID of the public/host subnet"
  value       = azurerm_subnet.public.id
}

output "public_subnet_address_prefix" {
  description = "Address prefix of the public/host subnet"
  value       = azurerm_subnet.public.address_prefixes[0]
}

output "private_subnet_name" {
  description = "Name of the private/container subnet"
  value       = azurerm_subnet.private.name
}

output "private_subnet_id" {
  description = "Resource ID of the private/container subnet"
  value       = azurerm_subnet.private.id
}

output "private_subnet_address_prefix" {
  description = "Address prefix of the private/container subnet"
  value       = azurerm_subnet.private.address_prefixes[0]
}

output "privatelink_subnet_name" {
  description = "Name of the Private Link subnet (if created)"
  value       = var.create_privatelink_subnet ? azurerm_subnet.privatelink[0].name : null
}

output "privatelink_subnet_id" {
  description = "Resource ID of the Private Link subnet (if created)"
  value       = var.create_privatelink_subnet ? azurerm_subnet.privatelink[0].id : null
}

output "privatelink_subnet_address_prefix" {
  description = "Address prefix of the Private Link subnet (if created)"
  value       = var.create_privatelink_subnet ? azurerm_subnet.privatelink[0].address_prefixes[0] : null
}

output "nsg_name" {
  description = "Name of the Network Security Group"
  value       = azurerm_network_security_group.this.name
}

output "nsg_id" {
  description = "Resource ID of the Network Security Group"
  value       = azurerm_network_security_group.this.id
}

output "public_subnet_nsg_association_id" {
  description = "Resource ID of the public subnet NSG association"
  value       = azurerm_subnet_network_security_group_association.public.id
}

output "private_subnet_nsg_association_id" {
  description = "Resource ID of the private subnet NSG association"
  value       = azurerm_subnet_network_security_group_association.private.id
}

output "nat_gateway_name" {
  description = "Name of the NAT Gateway (if created)"
  value       = var.enable_nat_gateway ? azurerm_nat_gateway.this[0].name : null
}

output "nat_gateway_id" {
  description = "Resource ID of the NAT Gateway (if created)"
  value       = var.enable_nat_gateway ? azurerm_nat_gateway.this[0].id : null
}

output "nat_gateway_public_ip" {
  description = "Public IP address of the NAT Gateway (if created)"
  value       = var.enable_nat_gateway ? azurerm_public_ip.nat[0].ip_address : null
}

output "key_vault_name" {
  description = "Name of the Key Vault (if created)"
  value       = var.create_key_vault ? module.key_vault[0].key_vault_name : null
}

output "key_vault_id" {
  description = "Resource ID of the Key Vault (if created)"
  value       = var.create_key_vault ? module.key_vault[0].key_vault_id : null
}

output "key_vault_uri" {
  description = "URI of the Key Vault (if created)"
  value       = var.create_key_vault ? module.key_vault[0].key_vault_uri : null
}

output "cmk_key_name" {
  description = "Name of the CMK key (if created)"
  value       = var.create_key_vault ? module.key_vault[0].key_name : null
}

output "cmk_key_id" {
  description = "Key Vault Key URI for CMK (if created) - Use for workspace encryption"
  value       = var.create_key_vault ? module.key_vault[0].key_id : null
}

# ==============================================
# Deployment Summary
# ==============================================

output "deployment_summary" {
  description = "Summary of BYOR deployment"
  value = <<-EOT

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ BYOR Deployment Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Resource Group: ${local.resource_group_name}
Location:       ${var.location}
VNet:           ${azurerm_virtual_network.this.name}
Address Space:  ${join(", ", azurerm_virtual_network.this.address_space)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Subnets Created:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Public/Host:     ${azurerm_subnet.public.name} (${join(", ", azurerm_subnet.public.address_prefixes)})
✅ Private/Container: ${azurerm_subnet.private.name} (${join(", ", azurerm_subnet.private.address_prefixes)})
${var.create_privatelink_subnet ? "✅ Private Link:     ${azurerm_subnet.privatelink[0].name} (${join(", ", azurerm_subnet.privatelink[0].address_prefixes)})" : "⚠️  Private Link:     Not created (Full-Private only)"}

All subnets include:
  ✅ Delegation: Microsoft.Databricks/workspaces
  ✅ Service Endpoints: Storage, KeyVault, EventHub

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Network Security:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ NSG: ${azurerm_network_security_group.this.name}
  ✅ Outbound: AzureDatabricks (443)
  ✅ Outbound: Storage (443)
  ✅ Outbound: EventHub (443)
  ✅ Inbound:  Worker-to-Worker (all ports)

${var.enable_nat_gateway ? "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nInternet Egress (NAT Gateway):\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n✅ NAT Gateway: ${azurerm_nat_gateway.this[0].name}\n✅ Public IP:   ${azurerm_public_ip.nat[0].ip_address}\n✅ Attached to: Public + Private subnets" : "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nInternet Egress:\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n⚠️  NAT Gateway: Not created (Full-Private pattern)"}

${var.create_key_vault ? "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nCustomer-Managed Keys (CMK):\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n✅ Key Vault:  ${module.key_vault[0].key_vault_name}\n✅ CMK Key:    ${module.key_vault[0].key_name}\n✅ Key Type:   ${var.cmk_key_type} (${var.cmk_key_size} bits)\n✅ Rotation:   Auto-rotate every 90 days\n\nKey Vault Resource ID:\n  ${module.key_vault[0].key_vault_id}\n\nKey Vault Key URI:\n  ${module.key_vault[0].key_id}" : "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nCustomer-Managed Keys (CMK):\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n⚠️  Key Vault not created (optional)"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Next Steps:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Copy the 'copy_paste_config' output
2. Paste into workspace deployment terraform.tfvars:
   - For Non-PL:      deployments/non-pl/terraform.tfvars
   - For Full-Private: deployments/full-private/terraform.tfvars
3. Deploy your Databricks workspace
4. (Optional) Reuse this infrastructure for multiple workspaces

View copy-paste config:
  terraform output copy_paste_config

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Infrastructure is Databricks-ready!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EOT
}
