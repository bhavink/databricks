***REMOVED*** ============================================================================
***REMOVED*** Unity Catalog Module - Provider Configuration
***REMOVED*** ============================================================================

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

***REMOVED*** ============================================================================
***REMOVED*** Unity Catalog Metastore (Account-Level)
***REMOVED*** Create new metastore following SRA pattern
***REMOVED*** Only created when NOT using an existing metastore (metastore_id is empty)
***REMOVED*** ============================================================================

resource "databricks_metastore" "this" {
  count         = local.use_existing_metastore ? 0 : 1
  provider      = databricks.account
  name          = "${var.region}-${var.prefix}-metastore"
  region        = var.region
  owner         = var.databricks_client_id ***REMOVED*** Service principal as owner (needed for workspace provider operations)
  force_destroy = false

  ***REMOVED*** No storage_root - following SRA pattern for flexibility
  ***REMOVED*** Storage credentials and external locations managed at workspace level

  ***REMOVED*** No depends_on - metastore is created independently of workspace
  ***REMOVED*** Only needs account provider which is always available
}

***REMOVED*** ============================================================================
***REMOVED*** Unity Catalog Metastore Data Access Configuration
***REMOVED*** TEMPORARILY COMMENTED - Will be added in Phase 2
***REMOVED*** ============================================================================

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

***REMOVED*** ============================================================================
***REMOVED*** Assign Metastore to Workspace
***REMOVED*** Uses existing metastore if provided, otherwise uses newly created one
***REMOVED*** ============================================================================

resource "databricks_metastore_assignment" "workspace_assignment" {
  provider             = databricks.account
  metastore_id         = local.effective_metastore_id
  workspace_id         = var.workspace_id
  default_catalog_name = "main"

  ***REMOVED*** Only depends on metastore creation if we're creating a new one
  depends_on = [
    databricks_metastore.this
  ]
}

***REMOVED*** ============================================================================
***REMOVED*** Workspace Admin Assignment via Unity Catalog
***REMOVED*** Flow: WS Created → UC Metastore Created → UC Assigned to WS → Add User as Admin
***REMOVED*** Uses account-level APIs to create user and grant workspace admin permission
***REMOVED*** ============================================================================

***REMOVED*** ============================================================================
***REMOVED*** Workspace Admin Assignment via Unity Catalog
***REMOVED*** TEMPORARILY DISABLED - Uncomment when ready to assign workspace admin
***REMOVED*** Reference: https://github.com/databricks/terraform-databricks-sra/blob/main/aws/tf/modules/databricks_account/user_assignment/main.tf
***REMOVED*** ============================================================================

***REMOVED*** ***REMOVED*** Look up the workspace admin user from account console
***REMOVED*** data "databricks_user" "workspace_admin" {
***REMOVED***   count = var.workspace_admin_email != "" ? 1 : 0
***REMOVED*** 
***REMOVED***   provider  = databricks.account
***REMOVED***   user_name = var.workspace_admin_email
***REMOVED*** }
***REMOVED*** 
***REMOVED*** ***REMOVED*** Assign user as workspace admin using account-level permission assignment
***REMOVED*** resource "databricks_mws_permission_assignment" "workspace_admin" {
***REMOVED***   count = var.workspace_admin_email != "" ? 1 : 0
***REMOVED*** 
***REMOVED***   provider     = databricks.account
***REMOVED***   workspace_id = var.workspace_id
***REMOVED***   principal_id = data.databricks_user.workspace_admin[0].id
***REMOVED***   permissions  = ["ADMIN"]
***REMOVED*** 
***REMOVED***   lifecycle {
***REMOVED***     ignore_changes = [principal_id]
***REMOVED***   }
***REMOVED*** 
***REMOVED***   depends_on = [
***REMOVED***     databricks_metastore_assignment.workspace_assignment
***REMOVED***   ]
***REMOVED*** }


