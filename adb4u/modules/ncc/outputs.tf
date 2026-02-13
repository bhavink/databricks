# ==============================================
# NCC Configuration Outputs
# ==============================================

output "ncc_id" {
  description = "Network Connectivity Configuration ID"
  value       = databricks_mws_network_connectivity_config.this.network_connectivity_config_id
}

output "ncc_name" {
  description = "Network Connectivity Configuration Name"
  value       = databricks_mws_network_connectivity_config.this.name
}

output "ncc_region" {
  description = "Network Connectivity Configuration Region"
  value       = databricks_mws_network_connectivity_config.this.region
}

output "ncc_binding_id" {
  description = "NCC Binding ID (NCC attached to workspace)"
  value       = databricks_mws_ncc_binding.this.id
}

output "workspace_id_numeric" {
  description = "Workspace ID that NCC is bound to"
  value       = databricks_mws_ncc_binding.this.workspace_id
}
