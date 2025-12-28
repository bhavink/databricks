data "databricks_sql_warehouse" "all" {
  provider = databricks.workspace
  for_each = var.provision_workspace_resources ? { for cfg in local.sqlwarehouse_config_map : cfg.name => cfg } : {}
  name     = each.value.name
  # MODIFICATION - added null_resource.wait_for_workspace_running dependency to make sure that workspace is in running state
  depends_on = [databricks_sql_endpoint.this, null_resource.wait_for_workspace_running]
}

resource "databricks_permissions" "endpoint_usage" {
  provider = databricks.workspace
  # MODIFICATION: This resource manages SQL warehouse (endpoint) permissions for Databricks SQL endpoints using the workspace-level provider.
  # For each configured SQL warehouse, permissions specified in the variable config will be applied to the appropriate groups.
  # This ensures fine-grained access control across all provisioned Databricks SQL endpoints, and is dependent on the workspace, endpoint, and group role assignments being fully provisioned and in a running state.
  for_each = var.provision_workspace_resources ? { for cfg in local.sqlwarehouse_config_map : cfg.name => cfg } : {}

  sql_endpoint_id = data.databricks_sql_warehouse.all[each.key].id

  dynamic "access_control" {
    for_each = flatten([for perm in each.value.permission : [for group in perm.group : { group = group, role = perm.role }]])
    content {
      group_name       = access_control.value.group
      permission_level = upper(access_control.value.role)
    }
  }
  # MODIFICATION - added null_resource.wait_for_workspace_running dependency to make sure that workspace is in running state
  depends_on = [
    databricks_sql_endpoint.this,
    null_resource.wait_for_workspace_running,
    databricks_mws_permission_assignment.add_group_role_user,
    databricks_mws_permission_assignment.add_group_role_admin
  ]
}
# resource "databricks_sql_permissions" "this" {
#   provider = databricks.workspace
#   cluster_id = 
#   table = "foo"
#   for_each = { for content in local.sqlwarehouse_config_map : content.name => content }
#   # Other permission-related attributes...
#   dynamic "privilege_assignments" {
#     for_each = flatten([for perm in each.value.permission : [for group in perm.group : { group = group, role = perm.role }]])
#    content {
#      principal = privilege_assignments.value.group
#      privileges = privilege_assignments.value.role == "writer" ? [
#       "CREATE","USAGE","MODIFY","SELECT","READ_METADATA","CREATE_NAMED_FUNCTION","MODIFY_CLASSPATH"
#       ] : privilege_assignments.value.role == "reader" ? [
#       "SELECT","READ_METADATA"
#       ]: privilege_assignments.value.role == "admin" ? ["ALL_PRIVILEGES"] : []
#    }
#   }
# }

