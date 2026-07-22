# ------------------------------------------------------------------
# Workspace group ASSIGNMENTS (references existing account groups).
#
# This flow does NOT create groups/users/GSAs — those are account-level and
# shared, managed out of band in ../identities/. Here we only look up groups that
# already exist and grant them a permission on THIS workspace.
#
# Input: var.workspace_groups = { "<existing-group-name>" = "ADMIN"|"USER" }
# Empty map = no group assignments.
# ------------------------------------------------------------------

# Look up each existing account group by display name.
data "databricks_group" "assigned" {
  provider     = databricks.accounts
  for_each     = var.workspace_groups
  display_name = each.key
}

# Assign each group to this workspace with its permission (ADMIN / USER).
# Ordered AFTER the metastore assignment: workspace identity/permission grants
# require the workspace to be bound to a metastore first.
resource "databricks_mws_permission_assignment" "this" {
  provider     = databricks.accounts
  for_each     = var.workspace_groups
  workspace_id = databricks_mws_workspaces.databricks_workspace.workspace_id
  principal_id = data.databricks_group.assigned[each.key].id
  permissions  = [each.value]

  depends_on = [databricks_metastore_assignment.this]
}
