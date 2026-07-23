# ------------------------------------------------------------------
# Serverless egress control (anti-exfil). Default OFF (enable_network_policy).
#
# Model:
#   - enable_network_policy = true, shared_network_policy_id = ""  -> create a
#     PER-WORKSPACE account network policy (RESTRICTED_ACCESS) from network_policy.yaml
#     and bind this workspace to it.
#   - shared_network_policy_id = "<id>"  -> bind to that EXISTING shared policy
#     instead (created out of band); no per-ws policy is created.
#   - enable_network_policy = false AND no shared id -> nothing; the workspace keeps
#     the account 'default-policy' (which is FULL_ACCESS / open egress).
#
# Enforcement defaults to DRY_RUN (log only) so it never breaks serverless on day 1.
# These are ACCOUNT-level resources (databricks.accounts provider).
#
# NOTE: databricks_workspace_network_option is UPDATE-ONLY — every workspace always
# has one (defaulting to 'default-policy'). Deleting this TF resource does NOT revert
# the workspace to default-policy on the backend; it stays pinned to the custom
# policy, and that policy then can't be deleted ("attached to N running workspaces").
# To turn off: set shared_network_policy_id = "default-policy" to rebind first, then
# remove the custom policy. See README "Serverless egress control" gotchas.
# ------------------------------------------------------------------

locals {
  # Create a per-workspace policy only when enabled AND not binding a shared one.
  create_ws_network_policy = var.enable_network_policy && var.shared_network_policy_id == ""

  # Allow-list from YAML (only when we're creating the per-ws policy).
  np_yaml = local.create_ws_network_policy ? yamldecode(file("${path.module}/network_policy.yaml")) : {}

  # Coalesce null/absent YAML keys to empty lists (a key with only commented
  # entries parses to null, which can't be iterated).
  np_internet = try(local.np_yaml.internet_destinations, null) == null ? [] : local.np_yaml.internet_destinations
  np_storage  = try(local.np_yaml.storage_destinations, null) == null ? [] : local.np_yaml.storage_destinations

  # Resolved policy id to bind: shared (if given) > created per-ws > "" (no binding).
  bound_network_policy_id = (
    var.shared_network_policy_id != "" ? var.shared_network_policy_id :
    local.create_ws_network_policy ? databricks_account_network_policy.this[0].network_policy_id :
    ""
  )
}

# Per-workspace serverless egress policy.
resource "databricks_account_network_policy" "this" {
  count             = local.create_ws_network_policy ? 1 : 0
  provider          = databricks.accounts
  network_policy_id = "${var.databricks_workspace_name}-np-${random_string.databricks_suffix.result}"

  egress = {
    network_access = {
      restriction_mode = "RESTRICTED_ACCESS"

      allowed_internet_destinations = [
        for d in local.np_internet : {
          destination               = d
          internet_destination_type = "DNS_NAME"
        }
      ]

      allowed_storage_destinations = [
        for b in local.np_storage : {
          bucket_name              = b
          storage_destination_type = "GOOGLE_CLOUD_STORAGE"
        }
      ]

      policy_enforcement = {
        enforcement_mode = var.network_policy_enforcement_mode
      }
    }
  }
}

# Bind the workspace to the resolved policy (shared or per-ws). Only at RUNNING, and
# only when a policy id is resolved; otherwise the workspace keeps 'default-policy'.
resource "databricks_workspace_network_option" "this" {
  count             = (local.bound_network_policy_id != "" && var.expected_workspace_status == "RUNNING") ? 1 : 0
  provider          = databricks.accounts
  workspace_id      = databricks_mws_workspaces.databricks_workspace.workspace_id
  network_policy_id = local.bound_network_policy_id
}

output "network_policy_id" {
  description = "The network policy bound to the workspace (empty if using default-policy)."
  value       = local.bound_network_policy_id
}
