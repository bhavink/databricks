# ------------------------------------------------------------------
# Workspace guardrails: the bare-minimum controls for any workspace.
#
#   1. Inbound: IP access lists on the workspace front-end (users and apps).
#   2. Serverless egress: a network connectivity config and an enforced
#      network policy (RESTRICTED_ACCESS) for serverless compute.
#
# Apply after any workspace deployment that doesn't include them (e.g. the
# byovpc-* roots). The lpw root has the same controls built in. Same model
# as lpw's ip-access-list.tf and network-policy.tf: entries live in
# ip_access_list.yaml and network_policy.yaml next to this file.
# ------------------------------------------------------------------

data "databricks_mws_workspaces" "all" {
  provider = databricks.accounts
}

locals {
  workspace_id = data.databricks_mws_workspaces.all.ids[var.databricks_workspace_name]

  ip_access_lists = var.enable_ip_access_list ? yamldecode(file("${path.module}/ip_access_list.yaml")) : {}

  create_network_policy = var.enable_network_policy && var.shared_network_policy_id == ""
  np_yaml               = local.create_network_policy ? yamldecode(file("${path.module}/network_policy.yaml")) : {}
  # A key with only commented entries parses to null.
  np_internet = try(local.np_yaml.internet_destinations, null) == null ? [] : local.np_yaml.internet_destinations
  np_storage  = try(local.np_yaml.storage_destinations, null) == null ? [] : local.np_yaml.storage_destinations

  bound_network_policy_id = (
    var.shared_network_policy_id != "" ? var.shared_network_policy_id :
    local.create_network_policy ? databricks_account_network_policy.this[0].network_policy_id : ""
  )
}

# ----------------------------------------------------------------- 1. inbound

# Enable the feature before adding entries. An ALLOW list restricts the
# workspace to the listed ranges only: include your own egress IP.
resource "databricks_workspace_conf" "ip_acl" {
  count    = var.enable_ip_access_list ? 1 : 0
  provider = databricks.workspace
  custom_config = {
    "enableIpAccessLists" = "true"
  }
}

resource "databricks_ip_access_list" "this" {
  for_each     = local.ip_access_lists
  provider     = databricks.workspace
  label        = each.key
  list_type    = each.value.list_type
  ip_addresses = each.value.ip_addresses

  depends_on = [databricks_workspace_conf.ip_acl]
}

# ----------------------------------------------------------------- 2. serverless egress

resource "databricks_mws_network_connectivity_config" "this" {
  count    = var.enable_ncc ? 1 : 0
  provider = databricks.accounts
  name     = "${substr(var.databricks_workspace_name, 0, 24)}-ncc"
  region   = var.google_region
}

resource "databricks_mws_ncc_binding" "this" {
  count                          = var.enable_ncc ? 1 : 0
  provider                       = databricks.accounts
  network_connectivity_config_id = databricks_mws_network_connectivity_config.this[0].network_connectivity_config_id
  workspace_id                   = local.workspace_id
}

resource "databricks_account_network_policy" "this" {
  count             = local.create_network_policy ? 1 : 0
  provider          = databricks.accounts
  network_policy_id = "${substr(var.databricks_workspace_name, 0, 40)}-serverless"
  account_id        = var.databricks_account_id

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

# Update-only on the backend: every workspace always has one. To turn the
# policy off later, bind "default-policy" first (shared_network_policy_id),
# then remove the custom policy.
resource "databricks_workspace_network_option" "this" {
  count             = local.bound_network_policy_id != "" ? 1 : 0
  provider          = databricks.accounts
  workspace_id      = local.workspace_id
  network_policy_id = local.bound_network_policy_id
}
