# ============================================================================
# Workspace Catalog Creation
# Uses root storage bucket when creating new metastore
# Uses external storage bucket when using existing metastore
# ============================================================================

resource "databricks_catalog" "workspace_catalog" {
  count = var.create_workspace_catalog ? 1 : 0

  provider = databricks.workspace
  name = var.workspace_catalog_name != "" ? (
    replace("${var.workspace_catalog_name}_${var.prefix}-catalog", "-", "_")
    ) : (
    replace("${var.prefix}-catalog", "-", "_")
  )
  comment        = "Workspace catalog for ${var.workspace_name}"
  isolation_mode = "OPEN"
  storage_root   = local.workspace_catalog_storage_root

  properties = {
    purpose = "Workspace catalog"
  }

  depends_on = [
    databricks_metastore_assignment.workspace_assignment,
    databricks_external_location.external_location
  ]
}

# ============================================================================
# Set Workspace Catalog as Default
# ============================================================================

resource "databricks_default_namespace_setting" "this" {
  count = var.create_workspace_catalog ? 1 : 0

  provider = databricks.workspace

  namespace {
    value = databricks_catalog.workspace_catalog[0].name
  }

  depends_on = [databricks_catalog.workspace_catalog]
}

