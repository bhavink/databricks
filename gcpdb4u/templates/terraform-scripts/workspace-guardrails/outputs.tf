output "workspace_id" {
  description = "Numeric ID of the secured workspace"
  value       = local.workspace_id
}

output "network_connectivity_config_id" {
  description = "NCC bound to the workspace (null when enable_ncc = false)"
  value       = var.enable_ncc ? databricks_mws_network_connectivity_config.this[0].network_connectivity_config_id : null
}

output "network_policy_id" {
  description = "Serverless network policy bound to the workspace (empty when none)"
  value       = local.bound_network_policy_id
}

output "ip_access_lists" {
  description = "IP access list labels applied to the workspace"
  value       = sort(keys(local.ip_access_lists))
}
