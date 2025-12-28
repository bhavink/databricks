resource "databricks_grants" "storage_credential_premissions" {
  provider = databricks.workspace
  for_each = var.provision_workspace_resources ? { for content in local.storage_credentials_permissions_map : content.name => content } : {}

  storage_credential = "${each.value.name}-storage-creds"
  dynamic "grant" {
    for_each = flatten([for perm in each.value.permission : [for group in perm.group : { group = group, role = perm.role }]])
    content {
      principal = grant.value.group
      privileges = grant.value.role == "writer" ? [
        "READ_FILES", "WRITE_FILES"
        ] : grant.value.role == "reader" ? [
        "READ_FILES"
      ] : grant.value.role == "admin" ? ["ALL_PRIVILEGES"] : []
    }

  }
  ***REMOVED*** MODIFICATION - added null_resource.wait_for_workspace_running dependency to make sure that workspace is in running state
  depends_on = [databricks_storage_credential.this, databricks_workspace_binding.storage_credential, null_resource.wait_for_workspace_running]
}


resource "databricks_grants" "external_location_permissions" {
  provider = databricks.workspace
  for_each = var.provision_workspace_resources ? { for content in local.external_location_permissions_map : content.name => content } : {}

  external_location = "${each.value.name}-ext-location"
  dynamic "grant" {
    for_each = flatten([for perm in each.value.permission : [for group in perm.group : { group = group, role = perm.role }]])
    content {
      principal = grant.value.group
      privileges = grant.value.role == "writer" ? [
        "READ_FILES", "WRITE_FILES", "BROWSE"
        ] : grant.value.role == "reader" ? [
        "READ_FILES", "BROWSE"
      ] : grant.value.role == "admin" ? ["ALL_PRIVILEGES"] : []
    }
  }
  ***REMOVED*** MODIFICATION - added null_resource.wait_for_workspace_running dependency to make sure that workspace is in running state
  depends_on = [databricks_external_location.external_location, databricks_workspace_binding.ext_loc, null_resource.wait_for_workspace_running]
}


resource "databricks_grants" "workspace_catalog_permission" {
  provider = databricks.workspace
  for_each = var.provision_workspace_resources ? { for content in local.unity_catalog_permissions_map : content.name => content } : {}

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
  ***REMOVED*** MODIFICATION - added null_resource.wait_for_workspace_running dependency to make sure that workspace is in running state
  depends_on = [databricks_catalog.workspace_catalog, databricks_workspace_binding.catalog, null_resource.wait_for_workspace_running]
}
