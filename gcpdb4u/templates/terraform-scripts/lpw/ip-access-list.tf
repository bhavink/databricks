# ------------------------------------------------------------------
# Workspace IP access lists (optional, default OFF via enable_ip_access_list).
#
# Applied ONLY after the workspace is RUNNING (apply 2) — these use the
# workspace-level provider, whose host is the workspace URL, so they can't run at
# PROVISIONING. Two steps, in order:
#   1. databricks_workspace_conf  -> enableIpAccessLists = true
#   2. databricks_ip_access_list  -> the ALLOW/BLOCK entries from the YAML
# Step 2 depends_on step 1 (the feature must be enabled before entries are added).
#
# Entries live in ip_access_list.yaml. When enable_ip_access_list = false, none of
# this is created (count = 0 / empty for_each).
#
# ⚠️ An ALLOW list restricts the workspace to the listed IPs only. Include your own
# egress IP/CIDR or you will lock yourself out of the UI/API.
# ------------------------------------------------------------------

locals {
  # IP ACLs use the workspace-level provider, so they can only be applied once the
  # workspace is RUNNING (apply 2) — the workspace URL isn't serving at PROVISIONING.
  # Gate on BOTH the feature flag AND the RUNNING phase.
  ip_acl_active = var.enable_ip_access_list && var.expected_workspace_status == "RUNNING"

  # Parse the YAML only when active; else empty map (no entries).
  ip_access_lists = local.ip_acl_active ? yamldecode(file("${path.module}/ip_access_list.yaml")) : {}
}

# Step 1: enable the feature on the workspace (RUNNING only).
resource "databricks_workspace_conf" "ip_acl" {
  count    = local.ip_acl_active ? 1 : 0
  provider = databricks.workspace
  custom_config = {
    "enableIpAccessLists" = "true"
  }
}

# Step 2: the ALLOW/BLOCK entries (RUNNING only, after step 1).
resource "databricks_ip_access_list" "this" {
  for_each     = local.ip_access_lists
  provider     = databricks.workspace
  label        = each.key
  list_type    = each.value.list_type
  ip_addresses = each.value.ip_addresses

  depends_on = [databricks_workspace_conf.ip_acl]
}
