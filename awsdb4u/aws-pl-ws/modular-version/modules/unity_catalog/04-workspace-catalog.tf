***REMOVED*** ============================================================================
***REMOVED*** Workspace Catalog Creation
***REMOVED*** ============================================================================

resource "databricks_catalog" "workspace_catalog" {
  count = var.create_workspace_catalog ? 1 : 0

  provider       = databricks.workspace
  name           = replace("${var.prefix}-catalog", "-", "_")
  comment        = "Workspace catalog for ${var.workspace_name}"
  isolation_mode = "OPEN"
  storage_root   = "s3://${var.unity_catalog_root_storage_bucket}/"

  properties = {
    purpose = "Workspace catalog"
  }

  depends_on = [
    databricks_metastore_assignment.workspace_assignment,
    databricks_external_location.root_storage[0]
  ]
}

***REMOVED*** ============================================================================
***REMOVED*** Set Workspace Catalog as Default
***REMOVED*** ============================================================================

resource "databricks_default_namespace_setting" "this" {
  count = var.create_workspace_catalog ? 1 : 0

  provider = databricks.workspace

  namespace {
    value = databricks_catalog.workspace_catalog[0].name
  }

  depends_on = [databricks_catalog.workspace_catalog]
}

