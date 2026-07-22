# MODIFICATION: Added deployment phase outputs
# Reason: Show current phase status and guide user to next deployment step

output "workspace_id" {
  value       = module.local_databricks.workspace_id
  description = "Databricks workspace ID"
}

output "workspace_url" {
  value       = module.local_databricks.workspace_url
  description = "Databricks workspace URL"
}

output "network_id" {
  value       = module.local_databricks.network_id
  description = "Databricks network configuration ID"
}

# MODIFICATION: Added workspace GSA email output
# Reason: Show workspace service account for manual addition to operator group
output "workspace_gsa_email" {
  value       = module.local_databricks.workspace_gsa_email
  description = "Workspace GSA (db-*) - MANUAL ACTION: Add to lpw-ws-operator@databricks.com"
}

output "current_phase" {
  value       = upper(var.phase)
  description = "Current deployment phase"
}

output "phase_status" {
  value       = upper(var.phase) == "PROVISIONING" ? "✅ Phase 1 (PROVISIONING) completed - Workspace created. MANUAL ACTION: Add workspace GSA to operator group" : "✅ Phase 2 (RUNNING) completed - All resources deployed!"
  description = "Current phase completion status"
}

output "manual_action_required" {
  value       = upper(var.phase) == "PROVISIONING" ? "⚠️  Add ${module.local_databricks.workspace_gsa_email} to lpw-ws-operator@databricks.com manually" : ""
  description = "Manual actions required after this phase"
}

output "next_command" {
  value       = upper(var.phase) == "PROVISIONING" ? "terraform apply -var=\"phase=RUNNING\"" : "Deployment complete"
  description = "Command for next phase"
}
