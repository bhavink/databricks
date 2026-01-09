***REMOVED*** ============================================================================
***REMOVED*** Unity Catalog Locals
***REMOVED*** ============================================================================

locals {
  ***REMOVED*** IAM role names based on workspace ID
  uc_iam_role_name      = "${var.prefix}-catalog-${var.workspace_id}"
  uc_root_iam_role_name = "${var.prefix}-root-storage-${var.workspace_id}"

  ***REMOVED*** ============================================================================
  ***REMOVED*** Conditional Logic for Existing Metastore Support
  ***REMOVED*** ============================================================================

  ***REMOVED*** Determine if using existing metastore
  use_existing_metastore = var.metastore_id != ""

  ***REMOVED*** Effective metastore ID (existing or newly created)
  effective_metastore_id = local.use_existing_metastore ? var.metastore_id : databricks_metastore.this[0].id

  ***REMOVED*** Storage root for workspace catalog
  ***REMOVED*** - New metastore: use root storage bucket
  ***REMOVED*** - Existing metastore: use external storage bucket
  workspace_catalog_storage_root = local.use_existing_metastore ? "s3://${var.unity_catalog_external_bucket}/" : "s3://${var.unity_catalog_root_storage_bucket}/"
}

