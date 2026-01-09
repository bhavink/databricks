***REMOVED*** ============================================================================
***REMOVED*** Grant Workspace Admin ALL_PRIVILEGES on Catalog
***REMOVED*** ============================================================================

resource "databricks_grant" "workspace_catalog_admin" {
  count = var.create_workspace_catalog ? 1 : 0

  provider = databricks.workspace
  catalog  = databricks_catalog.workspace_catalog[0].name

  principal  = var.workspace_admin_email
  privileges = ["ALL_PRIVILEGES"]

  depends_on = [
    databricks_catalog.workspace_catalog
  ]
}

***REMOVED*** ============================================================================
***REMOVED*** Grant Metastore Admin to Workspace Admin
***REMOVED*** Uses effective metastore ID (existing or newly created)
***REMOVED*** ============================================================================

resource "databricks_grant" "metastore_grants" {
  count = var.create_workspace_catalog ? 1 : 0

  provider  = databricks.workspace
  metastore = local.effective_metastore_id

  principal  = var.workspace_admin_email
  privileges = ["CREATE_CATALOG", "CREATE_EXTERNAL_LOCATION", "CREATE_STORAGE_CREDENTIAL"]

  depends_on = [
    databricks_metastore_assignment.workspace_assignment
  ]
}

***REMOVED*** ============================================================================
***REMOVED*** Grants for Root Storage Location
***REMOVED*** Only created when NOT using an existing metastore
***REMOVED*** ============================================================================

resource "databricks_grant" "root_storage_location_grants" {
  count = !local.use_existing_metastore && var.create_workspace_catalog ? 1 : 0

  provider          = databricks.workspace
  external_location = databricks_external_location.root_storage[0].id

  principal  = "account users"
  privileges = ["READ_FILES", "WRITE_FILES"]

  depends_on = [databricks_external_location.root_storage]
}

***REMOVED*** ============================================================================
***REMOVED*** Grants for External Location
***REMOVED*** ============================================================================

resource "databricks_grant" "external_location_grants" {
  count = var.create_workspace_catalog ? 1 : 0

  provider          = databricks.workspace
  external_location = databricks_external_location.external_location[0].id

  principal  = "account users"
  privileges = ["READ_FILES", "WRITE_FILES"]

  depends_on = [databricks_external_location.external_location]
}

