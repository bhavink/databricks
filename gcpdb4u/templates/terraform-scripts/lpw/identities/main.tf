# ==================================================================
# ACCOUNT-LEVEL IDENTITIES — groups, users, GSAs, memberships.
# SEPARATE Terraform + state from any workspace.
#
# Why separate: identities are ACCOUNT-scoped and shared across MANY workspaces.
# If a per-workspace deploy owned them, workspaces would fight over the same
# groups/users, and destroying one workspace would try to delete identities other
# workspaces still use. So identities live here, created once, and workspaces just
# REFERENCE them (see ../groups.tf, which looks them up by name and assigns them).
#
# Run from THIS directory with its OWN state:
#     cd identities/
#     export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)
#     terraform init && terraform apply
#
# Group topology + membership live in groups.yaml (edit there).
# ==================================================================

terraform {
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = ">=1.70.0"
    }
  }
}

provider "databricks" {
  alias                  = "accounts"
  host                   = "https://accounts.gcp.databricks.com"
  account_id             = var.databricks_account_id
  google_service_account = var.google_service_account_email
}

variable "databricks_account_id" {
  type        = string
  description = "Databricks account ID."
}

variable "google_service_account_email" {
  type        = string
  description = "GSA the provider impersonates (must be a Databricks account admin)."
}

locals {
  # Group topology + membership. Plain data — no workspace permissions here
  # (that is a per-workspace concern; see ../groups.tf).
  groups = yamldecode(file("${path.module}/groups.yaml"))

  # Deduplicated set of every member identity across all groups.
  all_members = toset(flatten([for g in local.groups : g.members]))

  # Flattened (group, member) pairs, keyed "group:member".
  memberships = merge([
    for gname, g in local.groups : {
      for m in g.members : "${gname}:${m}" => { group = gname, member = m }
    }
  ]...)
}

# Account groups.
resource "databricks_group" "this" {
  provider     = databricks.accounts
  for_each     = local.groups
  display_name = each.key
}

# Account users / GSAs. force = true adopts a principal that already exists.
# disable_as_user_deletion = true => on destroy, DEACTIVATE (never hard-delete),
# so tearing down this config can't remove a real human/GSA account.
resource "databricks_user" "this" {
  provider                 = databricks.accounts
  for_each                 = local.all_members
  user_name                = each.value
  force                    = true
  disable_as_user_deletion = true
}

# Membership edges.
resource "databricks_group_member" "this" {
  provider  = databricks.accounts
  for_each  = local.memberships
  group_id  = databricks_group.this[each.value.group].id
  member_id = databricks_user.this[each.value.member].id
}

output "group_ids" {
  description = "Map of group display_name => group id (for reference)."
  value       = { for k, g in databricks_group.this : k => g.id }
}
