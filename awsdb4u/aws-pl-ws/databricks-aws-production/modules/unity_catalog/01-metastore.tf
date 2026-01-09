# ============================================================================
# Unity Catalog Module - Provider Configuration
# ============================================================================

terraform {
  required_providers {
    databricks = {
      source                = "databricks/databricks"
      version               = "~> 1.0"
      configuration_aliases = [databricks.account, databricks.workspace]
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ============================================================================
# Unity Catalog Metastore (Account-Level)
# Create new metastore following SRA pattern
# Only created when NOT using an existing metastore (metastore_id is empty)
# ============================================================================

resource "databricks_metastore" "this" {
  count         = local.use_existing_metastore ? 0 : 1
  provider      = databricks.account
  name          = "${var.region}-${var.prefix}-metastore"
  region        = var.region
  owner         = var.databricks_client_id # Service principal as owner (needed for workspace provider operations)
  force_destroy = false

  # No storage_root - following SRA pattern for flexibility
  # Storage credentials and external locations managed at workspace level

  # No depends_on - metastore is created independently of workspace
  # Only needs account provider which is always available
}

# ============================================================================
# Unity Catalog Metastore Data Access Configuration
# TEMPORARILY COMMENTED - Will be added in Phase 2
# ============================================================================

/*
resource "databricks_metastore_data_access" "metastore_data_access" {
  provider     = databricks.account
  metastore_id = databricks_metastore.metastore.id
  name         = "${var.prefix}-metastore-access"
  aws_iam_role {
    role_arn = var.unity_catalog_role_arn
  }
  is_default = true

  depends_on = [
    databricks_metastore.this
  ]
}
*/

# ============================================================================
# Assign Metastore to Workspace
# Uses existing metastore if provided, otherwise uses newly created one
# ============================================================================

resource "databricks_metastore_assignment" "workspace_assignment" {
  provider             = databricks.account
  metastore_id         = local.effective_metastore_id
  workspace_id         = var.workspace_id
  default_catalog_name = "main"

  # Only depends on metastore creation if we're creating a new one
  depends_on = [
    databricks_metastore.this
  ]
}

# ============================================================================
# Workspace Admin Assignment via Unity Catalog
# Flow: WS Created → UC Metastore Created → UC Assigned to WS → Add User as Admin
# Uses account-level APIs to create user and grant workspace admin permission
# ============================================================================

# ============================================================================
# Workspace Admin Assignment via Unity Catalog
# TEMPORARILY DISABLED - Uncomment when ready to assign workspace admin
# Reference: https://github.com/databricks/terraform-databricks-sra/blob/main/aws/tf/modules/databricks_account/user_assignment/main.tf
# ============================================================================

# # Look up the workspace admin user from account console
# data "databricks_user" "workspace_admin" {
#   count = var.workspace_admin_email != "" ? 1 : 0
# 
#   provider  = databricks.account
#   user_name = var.workspace_admin_email
# }
# 
# # Assign user as workspace admin using account-level permission assignment
# resource "databricks_mws_permission_assignment" "workspace_admin" {
#   count = var.workspace_admin_email != "" ? 1 : 0
# 
#   provider     = databricks.account
#   workspace_id = var.workspace_id
#   principal_id = data.databricks_user.workspace_admin[0].id
#   permissions  = ["ADMIN"]
# 
#   lifecycle {
#     ignore_changes = [principal_id]
#   }
# 
#   depends_on = [
#     databricks_metastore_assignment.workspace_assignment
#   ]
# }


