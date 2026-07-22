
# data "databricks_catalog" "ext" {
#   provider     = databricks.workspace
#   for_each     = local.ext_unity_catalog_config_map
#   name         = "${each.value.name}"
# }

resource "databricks_workspace_binding" "ext_catalog" {
  provider       = databricks.workspace
  for_each       = var.provision_workspace_resources ? local.ext_unity_catalog_config_map : {}
  securable_name = each.value.name
  securable_type = "catalog"
  workspace_id   = databricks_mws_workspaces.dbx_workspace.workspace_id
  binding_type   = "BINDING_TYPE_READ_WRITE"
  depends_on     = [databricks_catalog.workspace_catalog, null_resource.wait_for_workspace_running]
}