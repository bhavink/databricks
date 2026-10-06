output "workspace_id" {
  description = "Numeric ID of the workspace (input to workspace-guardrails)"
  value       = tostring(databricks_mws_workspaces.this.workspace_id)
}

output "workspace_url" {
  description = "Workspace URL (input to workspace-guardrails)"
  value       = databricks_mws_workspaces.this.workspace_url
}
