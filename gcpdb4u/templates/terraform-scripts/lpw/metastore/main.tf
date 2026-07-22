# ==================================================================
# ONE-TIME, PER-REGION Unity Catalog metastore — SEPARATE Terraform + state.
#
# A metastore is a REGIONAL, account-level construct shared by ALL workspaces in
# that region. It is deliberately NOT in the per-workspace config (../): if it
# were, every workspace deploy would fight to own the shared metastore, and a
# `terraform destroy` of one demo could delete the metastore for every workspace
# in the region.
#
# Run this ONCE per region, from THIS directory, with its OWN state:
#     cd metastore/
#     export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)
#     terraform init && terraform apply
#
# If a metastore already exists for the region, DO NOT run apply — import it
# instead (see README.md) so you don't create a duplicate.
#
# NOTE on "automatically assign new workspaces": that account setting (default
# metastore for the region) is NOT exposed by the Terraform provider. It must be
# set once via the account console or REST API — see README.md. This config only
# creates the metastore (and optionally assigns specific existing workspaces).
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

variable "google_region" {
  type        = string
  description = "Region for the metastore. One metastore per region, shared by all workspaces in it."
}

variable "metastore_name" {
  type        = string
  default     = ""
  description = "Metastore name. Defaults to uc-<region> when empty."
}

variable "assign_workspace_ids" {
  type        = list(string)
  default     = []
  description = "Optional: existing workspace IDs in this region to assign to the metastore now. New workspaces are handled by the account-level auto-assign setting (see README), not here."
}

locals {
  metastore_name = var.metastore_name != "" ? var.metastore_name : "uc-${var.google_region}"
}

# The regional metastore. No storage_root: on GCP, Unity Catalog manages its own
# storage; a metastore-level storage_root is optional and omitted here.
resource "databricks_metastore" "this" {
  provider      = databricks.accounts
  name          = local.metastore_name
  region        = var.google_region
  force_destroy = false # regional shared resource — never casually destroy
}

# Optional: assign specific EXISTING workspaces now. Per-workspace only; there is
# no "assign all future workspaces" resource (that is the account auto-assign
# setting, done out of band — see README).
resource "databricks_metastore_assignment" "this" {
  provider     = databricks.accounts
  for_each     = toset(var.assign_workspace_ids)
  metastore_id = databricks_metastore.this.id
  workspace_id = each.value
}

output "metastore_id" {
  value = databricks_metastore.this.id
}

output "metastore_name" {
  value = databricks_metastore.this.name
}
