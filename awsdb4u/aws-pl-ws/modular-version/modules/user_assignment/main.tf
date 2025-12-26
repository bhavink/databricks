# ============================================================================
# Databricks Workspace User Assignment Module
# Reference: https://github.com/databricks/terraform-databricks-sra/tree/main/aws/tf/modules/databricks_account/user_assignment
# ============================================================================
# This module assigns an existing Databricks account user as workspace admin
# Prerequisites:
# - User must already exist in Databricks account console
# - Workspace must be assigned to a Unity Catalog metastore
# ============================================================================

# Look up the workspace admin user from account console
data "databricks_user" "workspace_access" {
  user_name = var.user_name
}

# Assign user as workspace admin using account-level permission assignment
resource "databricks_mws_permission_assignment" "workspace_access" {
  workspace_id = var.workspace_id
  principal_id = data.databricks_user.workspace_access.id
  permissions  = ["ADMIN"]

  lifecycle {
    ignore_changes = [principal_id]
  }
}

