output "workspace_id" {
  description = "Azure resource ID of the workspace"
  value       = azapi_resource.workspace.id
}

output "workspace_url" {
  description = "Workspace URL"
  value       = "https://${local.workspace_url}"
}

output "databricks_workspace_id" {
  description = "Numeric workspace ID (account console)"
  value       = local.workspace_id
}

output "ncc_id" {
  description = "Network connectivity configuration bound to the workspace"
  value       = databricks_mws_network_connectivity_config.this.network_connectivity_config_id
}

output "network_policy_id" {
  description = "Serverless network policy assigned to the workspace"
  value       = databricks_account_network_policy.this.network_policy_id
}
