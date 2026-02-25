# ============================================================================
# WORKSPACE GSA GROUP MEMBERSHIP - CURRENTLY DISABLED
# ============================================================================
# MODIFICATION: Workspace GSA group membership feature is COMMENTED OUT
# Reason: Missing required permissions to add service accounts to Google Workspace groups
#
# REQUIRED PERMISSION: ccc.hosted.frontend.directory.v1.DirectoryMembers.Insert
#
# REQUIREMENTS TO ENABLE THIS FEATURE:
# 1. Terraform must run as a Google Service Account (GSA)
# 2. That GSA must have domain-wide delegation enabled
# 3. The GSA must impersonate a Workspace admin user
# 4. The API call must be authorized as the admin user
#
# TO ENABLE: Uncomment the code below after configuring the above requirements
# ============================================================================

# Local variable to calculate workspace GSA email
# Format: db-<workspace-id>@prod-gcp-<region>.iam.gserviceaccount.com
locals {
  # Workspace GSA is created by Databricks immediately after workspace creation
  workspace_gsa_email = "db-${databricks_mws_workspaces.dbx_workspace.workspace_id}@prod-gcp-${var.google_region}.iam.gserviceaccount.com"
}

# COMMENTED OUT: Add workspace GSA as member of the pre-existing Google Workspace group
# Using googleworkspace_group_member resource (simpler than Cloud Identity API)
# resource "googleworkspace_group_member" "workspace_gsa_member" {
#   # MODIFICATION: Create membership in Phase 1 (PROVISIONING) if group email is provided
#   # Reason: Workspace GSA exists immediately after workspace creation, group membership needed before RUNNING
#   count    = var.workspace_operator_group_email != "" ? 1 : 0
#   
#   group_id = var.workspace_operator_group_email
#   email    = local.workspace_gsa_email
#   role     = "MEMBER"
#   
#   # MODIFICATION: Only depends on workspace creation
#   # Reason: Workspace GSA is created immediately when workspace resource is created
#   depends_on = [
#     databricks_mws_workspaces.dbx_workspace
#   ]
# }

