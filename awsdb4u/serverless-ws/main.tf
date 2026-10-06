# ------------------------------------------------------------------
# Serverless workspace: no VPC, no cross-account role, no root bucket.
# Compute runs in the Databricks serverless compute plane and data lives
# in default storage (or your buckets, through Unity Catalog).
#
# Apply ../workspace-guardrails next for the bare minimum (IP access lists,
# NCC, enforced serverless network policy) and the metastore assignment.
# A VPC is needed only for a private front-end (PrivateLink).
# ------------------------------------------------------------------

resource "databricks_mws_workspaces" "this" {
  provider       = databricks.accounts
  account_id     = var.databricks_account_id
  workspace_name = var.workspace_name
  aws_region     = var.region
  compute_mode   = "SERVERLESS"
  pricing_tier   = "ENTERPRISE"
}
