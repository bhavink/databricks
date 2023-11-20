/*
In this script we'll be using identity federation where in users and groups available on the account console will
be added to workspaces and workspace level permissions will be assigned

https://docs.gcp.databricks.com/administration-guide/users-groups/best-practices.html***REMOVED***sync-users-and-groups-from-your-identity-provider-to-your-databricks-account


*/

// add a group to account console
resource "databricks_group" "data_eng" {
  provider     = databricks.accounts
  display_name = var.group_name1
}

// add user
resource "databricks_user" "member0" { 
  provider     = databricks.accounts
  user_name = "${random_string.databricks_suffix.result}_de1@example.com"
  disable_as_user_deletion = false
}

// add user to a group
resource "databricks_group_member" "de_member0" {
  provider = databricks.accounts
  group_id  = databricks_group.data_eng.id
  member_id = databricks_user.member0.id
}

// add another group to account console
resource "databricks_group" "data_science" {
  provider     = databricks.accounts
  display_name = var.group_name2
}

// add user to group
resource "databricks_user" "member1" { 
  provider     = databricks.accounts
  user_name = "${random_string.databricks_suffix.result}_ds1@example.com"
  disable_as_user_deletion = false
}

// add one more user to a group
resource "databricks_group_member" "ds_member1" {
  provider = databricks.accounts
  group_id  = databricks_group.data_science.id
  member_id = databricks_user.member1.id
}

// identity federation takes approx 3 min to kick off upon a workspace creation and hence the sleep for 180seconds

resource "time_sleep" "wait_180_seconds" {
  depends_on = [
    databricks_group_member.ds_member1,
    databricks_group_member.de_member0
  ]
  create_duration = "180s"
}

// assign account level groups to workspace
resource "databricks_mws_permission_assignment" "add_admin_group" {
  depends_on = [
                databricks_mws_workspaces.databricks_workspace,
                time_sleep.wait_180_seconds
                ]
  provider = databricks.accounts
  workspace_id = local.workspace_id
  principal_id = databricks_group.data_science.id
  permissions  = ["ADMIN"]
}

// assign account level groups to workspace
resource "databricks_mws_permission_assignment" "add_non_admin_group" {
  depends_on = [
                databricks_mws_workspaces.databricks_workspace,
                time_sleep.wait_180_seconds
                ]
  provider = databricks.accounts
  workspace_id = local.workspace_id
  principal_id = databricks_group.data_eng.id
  permissions  = ["USER"]
}