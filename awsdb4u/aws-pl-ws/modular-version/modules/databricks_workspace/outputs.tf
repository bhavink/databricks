output "workspace_id" {
  description = "Databricks workspace ID"
  value       = databricks_mws_workspaces.workspace.workspace_id
}

output "workspace_url" {
  description = "Databricks workspace URL"
  value       = databricks_mws_workspaces.workspace.workspace_url
}

output "workspace_status" {
  description = "Databricks workspace status"
  value       = databricks_mws_workspaces.workspace.workspace_status
}

output "deployment_name" {
  description = "Databricks workspace deployment name"
  value       = databricks_mws_workspaces.workspace.deployment_name
}

output "credentials_id" {
  description = "MWS credentials ID"
  value       = databricks_mws_credentials.credentials.credentials_id
}

output "storage_configuration_id" {
  description = "MWS storage configuration ID"
  value       = databricks_mws_storage_configurations.storage.storage_configuration_id
}

output "network_id" {
  description = "MWS network ID"
  value       = databricks_mws_networks.network.network_id
}

output "private_access_settings_id" {
  description = "MWS private access settings ID"
  value       = databricks_mws_private_access_settings.private_access.private_access_settings_id
}

***REMOVED*** ============================================================================
***REMOVED*** IP Access Lists Outputs
***REMOVED*** ============================================================================

output "ip_access_lists_enabled" {
  description = "Whether IP access lists are enabled"
  value       = var.enable_ip_access_lists
}

output "ip_access_list_id" {
  description = "IP access list ID (if enabled)"
  value       = var.enable_ip_access_lists ? databricks_ip_access_list.allowed_list[0].id : null
}

