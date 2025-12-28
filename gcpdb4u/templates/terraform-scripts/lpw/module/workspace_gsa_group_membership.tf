***REMOVED*** ============================================================================
***REMOVED*** WORKSPACE GSA GROUP MEMBERSHIP - CURRENTLY DISABLED
***REMOVED*** ============================================================================
***REMOVED*** MODIFICATION: Workspace GSA group membership feature is COMMENTED OUT
***REMOVED*** Reason: Missing required permissions to add service accounts to Google Workspace groups
***REMOVED***
***REMOVED*** REQUIRED PERMISSION: ccc.hosted.frontend.directory.v1.DirectoryMembers.Insert
***REMOVED***
***REMOVED*** REQUIREMENTS TO ENABLE THIS FEATURE:
***REMOVED*** 1. Terraform must run as a Google Service Account (GSA)
***REMOVED*** 2. That GSA must have domain-wide delegation enabled
***REMOVED*** 3. The GSA must impersonate a Workspace admin user
***REMOVED*** 4. The API call must be authorized as the admin user
***REMOVED***
***REMOVED*** TO ENABLE: Uncomment the code below after configuring the above requirements
***REMOVED*** ============================================================================

***REMOVED*** Local variable to calculate workspace GSA email
***REMOVED*** Format: db-<workspace-id>@prod-gcp-<region>.iam.gserviceaccount.com
locals {
  ***REMOVED*** Workspace GSA is created by Databricks immediately after workspace creation
  workspace_gsa_email = "db-${databricks_mws_workspaces.dbx_workspace.workspace_id}@prod-gcp-${var.google_region}.iam.gserviceaccount.com"
}

***REMOVED*** COMMENTED OUT: Add workspace GSA as member of the pre-existing Google Workspace group
***REMOVED*** Using googleworkspace_group_member resource (simpler than Cloud Identity API)
***REMOVED*** resource "googleworkspace_group_member" "workspace_gsa_member" {
***REMOVED***   ***REMOVED*** MODIFICATION: Create membership in Phase 1 (PROVISIONING) if group email is provided
***REMOVED***   ***REMOVED*** Reason: Workspace GSA exists immediately after workspace creation, group membership needed before RUNNING
***REMOVED***   count    = var.workspace_operator_group_email != "" ? 1 : 0
***REMOVED***   
***REMOVED***   group_id = var.workspace_operator_group_email
***REMOVED***   email    = local.workspace_gsa_email
***REMOVED***   role     = "MEMBER"
***REMOVED***   
***REMOVED***   ***REMOVED*** MODIFICATION: Only depends on workspace creation
***REMOVED***   ***REMOVED*** Reason: Workspace GSA is created immediately when workspace resource is created
***REMOVED***   depends_on = [
***REMOVED***     databricks_mws_workspaces.dbx_workspace
***REMOVED***   ]
***REMOVED*** }

