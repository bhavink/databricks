# ============================================================================
# Grant Workspace Admin ALL_PRIVILEGES on Catalog
# ============================================================================

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

# ============================================================================
# Grant Metastore Admin to Workspace Admin
# ============================================================================

resource "databricks_grant" "metastore_grants" {
  count = var.create_workspace_catalog ? 1 : 0

  provider  = databricks.workspace
  metastore = databricks_metastore.this.id

  principal  = var.workspace_admin_email
  privileges = ["CREATE_CATALOG", "CREATE_EXTERNAL_LOCATION", "CREATE_STORAGE_CREDENTIAL"]

  depends_on = [
    databricks_metastore_assignment.workspace_assignment
  ]
}

# ============================================================================
# Grants for Root Storage Location
# ============================================================================

resource "databricks_grant" "root_storage_location_grants" {
  count = var.create_workspace_catalog ? 1 : 0

  provider          = databricks.workspace
  external_location = databricks_external_location.root_storage[0].id

  principal  = "account users"
  privileges = ["READ_FILES", "WRITE_FILES"]

  depends_on = [databricks_external_location.root_storage]
}

# ============================================================================
# Grants for External Location
# ============================================================================

resource "databricks_grant" "external_location_grants" {
  count = var.create_workspace_catalog ? 1 : 0

  provider          = databricks.workspace
  external_location = databricks_external_location.external_location[0].id

  principal  = "account users"
  privileges = ["READ_FILES", "WRITE_FILES"]

  depends_on = [databricks_external_location.external_location]
}

