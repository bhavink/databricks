***REMOVED***reference
***REMOVED***https://registry.terraform.io/providers/databricks/databricks/latest/docs/resources/workspace_binding

***REMOVED*** If you use workspaces to isolate user data access, you may want to limit access to catalog, 
***REMOVED*** external locations or storage credentials from specific workspaces in your account, also known as workspace binding
***REMOVED*** By default, Databricks assigns the securable to all workspaces attached to the current metastore. 
***REMOVED*** By using databricks_workspace_binding, the securable will be unassigned from all workspaces and only assigned explicitly using this resource.
***REMOVED*** Argument Reference

***REMOVED*** The following arguments are required:
***REMOVED*** workspace_id - ID of the workspace. Change forces creation of a new resource.
***REMOVED*** securable_name - Name of securable. Change forces creation of a new resource.
***REMOVED*** securable_type - Type of securable. Can be catalog, external-location or storage-credential. Default to catalog. Change forces creation of a new resource.
***REMOVED*** binding_type - (Optional) Binding mode. Default to BINDING_TYPE_READ_WRITE. Possible values are BINDING_TYPE_READ_ONLY, BINDING_TYPE_READ_WRITE.

resource "databricks_workspace_binding" "catalog" {
  provider       = databricks.workspace
  for_each       = var.provision_workspace_resources ? databricks_catalog.workspace_catalog : {}
  securable_name = each.value.name
  securable_type = "catalog"
  workspace_id   = databricks_mws_workspaces.dbx_workspace.workspace_id
  binding_type   = "BINDING_TYPE_READ_WRITE"

  ***REMOVED*** MODIFICATION: Added explicit workspace binding with dependencies
  ***REMOVED*** Reason: Ensure catalogs are accessible ONLY from this specific workspace
  depends_on = [
    databricks_catalog.workspace_catalog,
    databricks_workspace_binding.ext_loc,
    null_resource.wait_for_workspace_running
  ]
}

resource "databricks_workspace_binding" "ext_loc" {
  provider       = databricks.workspace
  for_each       = var.provision_workspace_resources ? databricks_external_location.external_location : {}
  securable_name = each.value.name
  securable_type = "external_location"
  workspace_id   = databricks_mws_workspaces.dbx_workspace.workspace_id
  binding_type   = "BINDING_TYPE_READ_WRITE"

  ***REMOVED*** MODIFICATION: Added explicit workspace binding with dependencies
  ***REMOVED*** Reason: Ensure external locations are accessible ONLY from this specific workspace
  depends_on = [
    databricks_external_location.external_location,
    databricks_workspace_binding.storage_credential,
    null_resource.wait_for_workspace_running
  ]
}


resource "databricks_workspace_binding" "storage_credential" {
  provider       = databricks.workspace
  for_each       = var.provision_workspace_resources ? databricks_storage_credential.this : {}
  securable_name = each.value.name
  securable_type = "storage_credential"
  workspace_id   = databricks_mws_workspaces.dbx_workspace.workspace_id
  binding_type   = "BINDING_TYPE_READ_WRITE"

  ***REMOVED*** MODIFICATION: Added explicit workspace binding with dependencies
  ***REMOVED*** Reason: Ensure storage credentials are accessible ONLY from this specific workspace
  depends_on = [
    databricks_storage_credential.this,
    databricks_metastore_assignment.this,
    null_resource.wait_for_workspace_running
  ]
}