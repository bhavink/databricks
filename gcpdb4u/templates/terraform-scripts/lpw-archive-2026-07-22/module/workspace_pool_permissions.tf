resource "databricks_permissions" "pool_usage" {
  provider = databricks.workspace
  # MODIFICATION - This resource assigns usage permissions for each instance pool to groups based on local.pool_usage_permissions_map.
  # Permissions are applied dynamically per pool and group.
  for_each = var.provision_workspace_resources ? databricks_instance_pool.compute_pools : {}

  instance_pool_id = each.value.id

  dynamic "access_control" {
    for_each = flatten([for perm in local.pool_usage_permissions_map : [for group in perm.group : { group = group, role = perm.role }]])
    content {
      group_name       = access_control.value.group
      permission_level = upper(access_control.value.role)
    }
  }
  # MODIFICATION - permissions for pool access assigned dynamically per group and role via access_control block
  # MODIFICATION - added null_resource.wait_for_workspace_running dependency to make sure that workspace is in running state
  depends_on = [
    null_resource.wait_for_workspace_running,
    databricks_mws_permission_assignment.add_group_role_user,
    databricks_mws_permission_assignment.add_group_role_admin
  ]
}