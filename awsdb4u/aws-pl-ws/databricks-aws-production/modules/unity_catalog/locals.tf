# ============================================================================
# Unity Catalog Locals
# ============================================================================

locals {
  # IAM role names based on workspace ID
  uc_iam_role_name      = "${var.prefix}-catalog-${var.workspace_id}"
  uc_root_iam_role_name = "${var.prefix}-root-storage-${var.workspace_id}"

  # ============================================================================
  # Conditional Logic for Existing Metastore Support
  # ============================================================================

  # Determine if using existing metastore
  use_existing_metastore = var.metastore_id != ""

  # Effective metastore ID (existing or newly created)
  effective_metastore_id = local.use_existing_metastore ? var.metastore_id : databricks_metastore.this[0].id

  # Storage root for workspace catalog
  # - New metastore: use root storage bucket
  # - Existing metastore: use external storage bucket
  workspace_catalog_storage_root = local.use_existing_metastore ? "s3://${var.unity_catalog_external_bucket}/" : "s3://${var.unity_catalog_root_storage_bucket}/"
}

