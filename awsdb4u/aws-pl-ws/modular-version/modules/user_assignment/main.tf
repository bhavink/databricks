***REMOVED*** ============================================================================
***REMOVED*** Databricks Workspace User Assignment Module
***REMOVED*** Reference: https://github.com/databricks/terraform-databricks-sra/tree/main/aws/tf/modules/databricks_account/user_assignment
***REMOVED*** ============================================================================
***REMOVED*** This module assigns an existing Databricks account user as workspace admin
***REMOVED*** Prerequisites:
***REMOVED*** - User must already exist in Databricks account console
***REMOVED*** - Workspace must be assigned to a Unity Catalog metastore
***REMOVED*** ============================================================================

***REMOVED*** Look up the workspace admin user from account console
data "databricks_user" "workspace_access" {
  user_name = var.user_name
}

***REMOVED*** Assign user as workspace admin using account-level permission assignment
resource "databricks_mws_permission_assignment" "workspace_access" {
  workspace_id = var.workspace_id
  principal_id = data.databricks_user.workspace_access.id
  permissions  = ["ADMIN"]

  lifecycle {
    ignore_changes = [principal_id]
  }
}

