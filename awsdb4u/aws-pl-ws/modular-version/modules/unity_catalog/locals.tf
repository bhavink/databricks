# ============================================================================
# Unity Catalog Locals
# ============================================================================

locals {
  # IAM role names based on workspace ID
  uc_iam_role_name      = "${var.prefix}-catalog-${var.workspace_id}"
  uc_root_iam_role_name = "${var.prefix}-root-storage-${var.workspace_id}"
}

