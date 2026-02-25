resource "databricks_mws_permission_assignment" "add_group_role_admin" {
  for_each     = (var.provision_workspace_resources && local.create_group_admin) ? data.databricks_group.group_role_admin : {}
  provider     = databricks.accounts
  workspace_id = databricks_mws_workspaces.dbx_workspace.workspace_id
  principal_id = each.value.id
  permissions  = ["ADMIN"]
  depends_on   = [databricks_mws_workspaces.dbx_workspace, databricks_metastore_assignment.this, null_resource.wait_for_workspace_running]
  # MODIFICATION - resource for assigning ADMIN role to groups
  # MODIFICATION - we wait for workspace to be in running state (using null_resource.wait_for_workspace_running in depends_on)
}

resource "databricks_mws_permission_assignment" "add_group_role_user" {
  for_each     = (var.provision_workspace_resources && local.create_group_user) ? data.databricks_group.group_role_user : {}
  provider     = databricks.accounts
  workspace_id = databricks_mws_workspaces.dbx_workspace.workspace_id
  principal_id = each.value.id
  permissions  = ["USER"]
  depends_on   = [databricks_mws_workspaces.dbx_workspace, databricks_metastore_assignment.this, null_resource.wait_for_workspace_running]
  # MODIFICATION - resource for assigning USER role to groups
  # MODIFICATION - we wait for workspace to be in running state (using null_resource.wait_for_workspace_running in depends_on)
}

resource "databricks_mws_permission_assignment" "add_user_role_user" {
  for_each     = (var.provision_workspace_resources && local.create_user_user) ? data.databricks_user.user_role_user : {}
  provider     = databricks.accounts
  workspace_id = databricks_mws_workspaces.dbx_workspace.workspace_id
  principal_id = each.value.id
  permissions  = ["USER"]
  depends_on   = [databricks_mws_workspaces.dbx_workspace, databricks_metastore_assignment.this, null_resource.wait_for_workspace_running]
  # MODIFICATION - resource for assigning USER role to users
  # MODIFICATION - we wait for workspace to be in running state (using null_resource.wait_for_workspace_running in depends_on)
}

resource "databricks_mws_permission_assignment" "add_user_role_admin" {
  for_each     = (var.provision_workspace_resources && local.create_user_admin) ? data.databricks_user.user_role_user : {}
  provider     = databricks.accounts
  workspace_id = databricks_mws_workspaces.dbx_workspace.workspace_id
  principal_id = each.value.id
  permissions  = ["ADMIN"]
  depends_on   = [databricks_mws_workspaces.dbx_workspace, databricks_metastore_assignment.this, null_resource.wait_for_workspace_running]
  # MODIFICATION - resource for assigning ADMIN role to users
  # MODIFICATION - we wait for workspace to be in running state (using null_resource.wait_for_workspace_running in depends_on)
}

resource "databricks_mws_permission_assignment" "add_spn_role_user" {
  for_each     = (var.provision_workspace_resources && local.create_spn_user) ? data.databricks_service_principal.spn_role_user : {}
  provider     = databricks.accounts
  workspace_id = databricks_mws_workspaces.dbx_workspace.workspace_id
  principal_id = each.value.id
  permissions  = ["USER"]
  depends_on   = [databricks_mws_workspaces.dbx_workspace, databricks_metastore_assignment.this, null_resource.wait_for_workspace_running]
  # MODIFICATION - resource for assigning USER role to service principals
  # MODIFICATION - we wait for workspace to be in running state (using null_resource.wait_for_workspace_running in depends_on)
}

resource "databricks_mws_permission_assignment" "add_spn_role_admin" {
  for_each     = (var.provision_workspace_resources && local.create_spn_admin) ? data.databricks_service_principal.spn_role_admin : {}
  provider     = databricks.accounts
  workspace_id = databricks_mws_workspaces.dbx_workspace.workspace_id
  principal_id = each.value.id
  permissions  = ["ADMIN"]
  depends_on   = [databricks_mws_workspaces.dbx_workspace, databricks_metastore_assignment.this, null_resource.wait_for_workspace_running]
  # MODIFICATION - resource for assigning ADMIN role to service principals
  # MODIFICATION - we wait for workspace to be in running state (using null_resource.wait_for_workspace_running in depends_on)
}
