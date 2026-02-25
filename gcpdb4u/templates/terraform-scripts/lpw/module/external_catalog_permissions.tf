

resource "databricks_grants" "ext_workspace_catalog_permission" {
  provider = databricks.workspace
  for_each = var.provision_workspace_resources ? { for content in local.ext_unity_catalog_permissions_map : content.name => content } : {}

  catalog = each.value.name

  dynamic "grant" {
    for_each = flatten([for perm in each.value.permission : [for group in perm.group : { group = group, role = perm.role }]])
    content {
      principal = grant.value.group
      privileges = grant.value.role == "data_writer" ? [
        "USE_CATALOG", "USE_SCHEMA", "APPLY_TAG", "MODIFY", "BROWSE", "READ_VOLUME",
        "SELECT", "WRITE_VOLUME", "CREATE_FUNCTION", "CREATE_MATERIALIZED_VIEW", "CREATE_MODEL", "CREATE_SCHEMA",
        "CREATE_TABLE", "CREATE_VOLUME"
        ] : grant.value.role == "data_reader" ? [
        "USE_CATALOG", "USE_SCHEMA", "BROWSE", "EXECUTE", "READ_VOLUME", "SELECT"
      ] : grant.value.role == "data_editor" ? ["ALL_PRIVILEGES"] : []
    }
  }
  # MODIFICATION - added null_resource.wait_for_workspace_running dependency to make sure that workspace is in running state
  depends_on = [databricks_workspace_binding.ext_catalog, null_resource.wait_for_workspace_running]
}