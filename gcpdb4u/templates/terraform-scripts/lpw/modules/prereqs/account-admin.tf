# ------------------------------------------------------------------
# Account-level admin role grant.
#
# This is DISTINCT from workspace permissions (databricks_mws_permission_assignment
# in groups.tf, which grants ADMIN/USER on a specific workspace). "account_admin"
# grants full Databricks account-console admin privileges.
#
# The GSA is registered as a user principal (see groups.tf), so it is granted the
# role via databricks_user_role, referencing the existing user resource.
#
# !!! SECURITY CONCERN !!!
# "account_admin" is the highest privilege in Databricks: it grants full control
# over the ENTIRE account, not just this workspace. That includes every workspace,
# billing, all identities/groups, network and security settings, and audit config.
# Granting this to a workspace compute service account is a large blast radius and
# a standing privilege-escalation path if that SA's credentials are ever exposed.
# Prefer scoping the GSA to the least privilege it actually needs (e.g. workspace
# ADMIN via databricks_mws_permission_assignment in groups.tf) unless account-wide
# administration is a hard requirement.
# ------------------------------------------------------------------

# resource "databricks_user_role" "gsa_account_admin" {
#   provider = databricks.accounts
#   user_id  = databricks_user.this[local.workspace_gsa].id
#   role     = "account_admin"
# }

# ------------------------------------------------------------------
# Alternative: grant to a hardcoded GSA email (not managed elsewhere).
# Use this ONLY if the GSA is not already declared as a databricks_user
# (referencing the managed resource above is preferred to avoid duplicates).
# Create the user, then attach the account_admin role to it.
# ------------------------------------------------------------------
# resource "databricks_user" "hardcoded_gsa" {
#   provider  = databricks.accounts
#   user_name = "my-gsa@my-project.iam.gserviceaccount.com"
#   force     = true # adopt the user if it already exists at the account level
# }
#
# resource "databricks_user_role" "hardcoded_gsa_account_admin" {
#   provider = databricks.accounts
#   user_id  = databricks_user.hardcoded_gsa.id
#   role     = "account_admin"
# }
