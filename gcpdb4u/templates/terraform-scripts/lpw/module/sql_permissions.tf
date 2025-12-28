data "databricks_sql_warehouse" "all" {
  provider = databricks.workspace
  for_each = var.provision_workspace_resources ? { for cfg in local.sqlwarehouse_config_map : cfg.name => cfg } : {}
  name     = each.value.name
  ***REMOVED*** MODIFICATION - added null_resource.wait_for_workspace_running dependency to make sure that workspace is in running state
  depends_on = [databricks_sql_endpoint.this, null_resource.wait_for_workspace_running]
}

resource "databricks_permissions" "endpoint_usage" {
  provider = databricks.workspace
  ***REMOVED*** MODIFICATION: This resource manages SQL warehouse (endpoint) permissions for Databricks SQL endpoints using the workspace-level provider.
  ***REMOVED*** For each configured SQL warehouse, permissions specified in the variable config will be applied to the appropriate groups.
  ***REMOVED*** This ensures fine-grained access control across all provisioned Databricks SQL endpoints, and is dependent on the workspace, endpoint, and group role assignments being fully provisioned and in a running state.
  for_each = var.provision_workspace_resources ? { for cfg in local.sqlwarehouse_config_map : cfg.name => cfg } : {}

  sql_endpoint_id = data.databricks_sql_warehouse.all[each.key].id

  dynamic "access_control" {
    for_each = flatten([for perm in each.value.permission : [for group in perm.group : { group = group, role = perm.role }]])
    content {
      group_name       = access_control.value.group
      permission_level = upper(access_control.value.role)
    }
  }
  ***REMOVED*** MODIFICATION - added null_resource.wait_for_workspace_running dependency to make sure that workspace is in running state
  depends_on = [
    databricks_sql_endpoint.this,
    null_resource.wait_for_workspace_running,
    databricks_mws_permission_assignment.add_group_role_user,
    databricks_mws_permission_assignment.add_group_role_admin
  ]
}
***REMOVED*** resource "databricks_sql_permissions" "this" {
***REMOVED***   provider = databricks.workspace
***REMOVED***   cluster_id = 
***REMOVED***   table = "foo"
***REMOVED***   for_each = { for content in local.sqlwarehouse_config_map : content.name => content }
***REMOVED***   ***REMOVED*** Other permission-related attributes...
***REMOVED***   dynamic "privilege_assignments" {
***REMOVED***     for_each = flatten([for perm in each.value.permission : [for group in perm.group : { group = group, role = perm.role }]])
***REMOVED***    content {
***REMOVED***      principal = privilege_assignments.value.group
***REMOVED***      privileges = privilege_assignments.value.role == "writer" ? [
***REMOVED***       "CREATE","USAGE","MODIFY","SELECT","READ_METADATA","CREATE_NAMED_FUNCTION","MODIFY_CLASSPATH"
***REMOVED***       ] : privilege_assignments.value.role == "reader" ? [
***REMOVED***       "SELECT","READ_METADATA"
***REMOVED***       ]: privilege_assignments.value.role == "admin" ? ["ALL_PRIVILEGES"] : []
***REMOVED***    }
***REMOVED***   }
***REMOVED*** }

