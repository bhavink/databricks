# ============================================================================
# User Assignment Module - Outputs
# ============================================================================

output "user_id" {
  description = "ID of the user assigned as workspace admin"
  value       = data.databricks_user.workspace_access.id
}

output "permission_assignment_id" {
  description = "ID of the workspace permission assignment"
  value       = databricks_mws_permission_assignment.workspace_access.id
}

output "user_name" {
  description = "Email address of the workspace admin"
  value       = data.databricks_user.workspace_access.user_name
}

