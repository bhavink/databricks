output "workspace_url" {
  description = "Databricks workspace URL"
  value       = "https://${azurerm_databricks_workspace.this.workspace_url}"
}

output "workspace_id" {
  description = "Databricks workspace ID (Azure resource ID)"
  value       = azurerm_databricks_workspace.this.id
}

output "workspace_id_numeric" {
  description = "Databricks workspace ID (numeric, for UC / API)"
  value       = azurerm_databricks_workspace.this.workspace_id
}

output "nat_gateway_public_ip" {
  description = "NAT Gateway public IP (egress for clusters)"
  value       = azurerm_public_ip.nat.ip_address
}

output "resource_group_name" {
  description = "Resource group name"
  value       = azurerm_resource_group.this.name
}
