output "workspace_id" {
  description = "Numeric ID of the workspace"
  value       = databricks_mws_workspaces.this.workspace_id
}

output "workspace_url" {
  description = "Workspace URL (input to workspace-guardrails)"
  value       = databricks_mws_workspaces.this.workspace_url
}
