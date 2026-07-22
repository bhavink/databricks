# Input variables are declared in variables.tf

data "google_client_openid_userinfo" "me" {}
data "google_client_config" "current" {}


# Random suffix for databricks network and workspace
resource "random_string" "databricks_suffix" {
  special = false
  upper   = false
  length  = 2
}

# Provision databricks CMK configuration
resource "databricks_mws_customer_managed_keys" "databricks_cmk_config" {
  provider   = databricks.accounts
  account_id = var.databricks_account_id
  gcp_key_info {
    kms_key_id = module.prereqs.crypto_key_id
  }
  use_cases = ["STORAGE", "MANAGED_SERVICES"]
  lifecycle {
    ignore_changes = all
  }
}

output "databricks_customer_managed_key_id" {
  value     = databricks_mws_customer_managed_keys.databricks_cmk_config.customer_managed_key_id
  sensitive = false
}


# Private Access Settings (PSC). Created only when enable_private_access = true.
# Attached to the workspace only at RUNNING (see below). Default off = standard
# public workspace. PAS defaults to hybrid (public access enabled, ACCOUNT level)
# via variables — the PSC path is added alongside public access by default.
resource "databricks_mws_private_access_settings" "pas" {
  count                        = var.enable_private_access ? 1 : 0
  provider                     = databricks.accounts
  region                       = var.google_region
  private_access_settings_name = "${var.databricks_workspace_name}-pas-${random_string.databricks_suffix.result}"
  # Defaults to the LPW posture (public ON, ACCOUNT); overridable via variables.
  public_access_enabled = var.public_access_enabled
  private_access_level  = var.private_access_level
}

output "databricks_private_access_settings_id" {
  value     = var.enable_private_access ? databricks_mws_private_access_settings.pas[0].private_access_settings_id : null
  sensitive = false
}

# Network Connectivity Config. Created only when enable_ncc = true; attached to
# the workspace only at RUNNING (see below). Regional — must match the workspace
# region. Name is 3-30 chars: [0-9a-zA-Z-_].
resource "databricks_mws_network_connectivity_config" "ncc" {
  count    = var.enable_ncc ? 1 : 0
  provider = databricks.accounts
  name     = "${substr(var.databricks_workspace_name, 0, 24)}-ncc"
  region   = var.google_region
}

output "databricks_network_connectivity_config_id" {
  value     = var.enable_ncc ? databricks_mws_network_connectivity_config.ncc[0].network_connectivity_config_id : null
  sensitive = false
}

# Databricks-side registration of the GCP PSC forwarding rules created in
# module.prereqs. Only when enable_private_access = true. These vpc_endpoint_ids
# are wired into the network's vpc_endpoints block for back-end PSC.
resource "databricks_mws_vpc_endpoint" "workspace_vpce" {
  count             = var.enable_private_access ? 1 : 0
  provider          = databricks.accounts
  account_id        = var.databricks_account_id
  vpc_endpoint_name = "${var.databricks_workspace_name}-workspace-vpce-${random_string.databricks_suffix.result}"
  gcp_vpc_endpoint_info {
    project_id        = local.vpc_project_id
    psc_endpoint_name = module.prereqs.psc_workspace_ep_name
    endpoint_region   = var.google_region
  }
}

resource "databricks_mws_vpc_endpoint" "relay_vpce" {
  count             = var.enable_private_access ? 1 : 0
  provider          = databricks.accounts
  account_id        = var.databricks_account_id
  vpc_endpoint_name = "${var.databricks_workspace_name}-relay-vpce-${random_string.databricks_suffix.result}"
  gcp_vpc_endpoint_info {
    project_id        = local.vpc_project_id
    psc_endpoint_name = module.prereqs.psc_relay_ep_name
    endpoint_region   = var.google_region
  }
}

# Provision databricks network configuration
resource "databricks_mws_networks" "databricks_network" {
  provider   = databricks.accounts
  account_id = var.databricks_account_id
  # name needs to be of length 3-30 incuding [a-z,A-Z,-_]
  network_name = "${var.databricks_workspace_name}-nw-${random_string.databricks_suffix.result}"
  gcp_network_info {
    network_project_id = local.vpc_project_id
    vpc_id             = module.prereqs.vpc_name
    subnet_id          = module.prereqs.subnet_name
    subnet_region      = var.google_region
  }

  # Back-end PSC: bind the registered endpoints. Only when private access is on.
  dynamic "vpc_endpoints" {
    for_each = var.enable_private_access ? [1] : []
    content {
      dataplane_relay = [databricks_mws_vpc_endpoint.relay_vpce[0].vpc_endpoint_id]
      rest_api        = [databricks_mws_vpc_endpoint.workspace_vpce[0].vpc_endpoint_id]
    }
  }
}

output "databricks_workspace_network_id" {
  value     = databricks_mws_networks.databricks_network.network_id
  sensitive = false
}

output "databricks_workspace_vpce_id" {
  value     = var.enable_private_access ? databricks_mws_vpc_endpoint.workspace_vpce[0].vpc_endpoint_id : null
  sensitive = false
}

output "databricks_relay_vpce_id" {
  value     = var.enable_private_access ? databricks_mws_vpc_endpoint.relay_vpce[0].vpc_endpoint_id : null
  sensitive = false
}

resource "databricks_mws_workspaces" "databricks_workspace" {
  provider       = databricks.accounts
  account_id     = var.databricks_account_id
  workspace_name = "${var.databricks_workspace_name}-${random_string.databricks_suffix.result}"
  location       = var.google_region

  cloud_resource_container {
    gcp {
      project_id = var.google_project_id
    }
  }

  # Phase selection: PROVISIONING (apply 1) then RUNNING (apply 2).
  expected_workspace_status = var.expected_workspace_status

  # ---------------------------------------------------------
  # Least-privilege workspace (LPW) flow: the API REJECTS all "cloud resource
  # configuration IDs" at creation (PROVISIONING) — including network_id — and
  # requires them in the update step (RUNNING). During PROVISIONING the workspace
  # is created bare so its gcp_workspace_sa is emitted and can be granted the
  # required roles; only then can these attach. Each is null during PROVISIONING:
  #   - network_id
  #   - CMK (storage + managed_services)
  #   - PAS (private_access_settings_id)
  #   - NCC (network_connectivity_config_id)
  # ---------------------------------------------------------
  network_id = var.expected_workspace_status == "RUNNING" ? databricks_mws_networks.databricks_network.network_id : null
  # CMK for both use cases (matches use_cases = ["STORAGE","MANAGED_SERVICES"]).
  storage_customer_managed_key_id          = var.expected_workspace_status == "RUNNING" ? databricks_mws_customer_managed_keys.databricks_cmk_config.customer_managed_key_id : null
  managed_services_customer_managed_key_id = var.expected_workspace_status == "RUNNING" ? databricks_mws_customer_managed_keys.databricks_cmk_config.customer_managed_key_id : null
  # PAS attaches only at RUNNING, and only when enable_private_access = true.
  private_access_settings_id = (var.expected_workspace_status == "RUNNING" && var.enable_private_access) ? databricks_mws_private_access_settings.pas[0].private_access_settings_id : null
  # NCC attaches only at RUNNING, and only when enable_ncc = true.
  network_connectivity_config_id = (var.expected_workspace_status == "RUNNING" && var.enable_ncc) ? databricks_mws_network_connectivity_config.ncc[0].network_connectivity_config_id : null
}

output "databricks_workspace_url" {
  value     = databricks_mws_workspaces.databricks_workspace.workspace_url
  sensitive = false
}

output "databricks_workspace_resource_id" {
  value     = databricks_mws_workspaces.databricks_workspace.workspace_id
  sensitive = false
}

output "databricks_workspace_gsa" {
  value     = databricks_mws_workspaces.databricks_workspace.gcp_workspace_sa
  sensitive = false
}

output "databricks_workspace_status" {
  value     = databricks_mws_workspaces.databricks_workspace.workspace_status
  sensitive = false
}

# Resolve the metastore for binding. Whether identified by name or by explicit ID,
# read it back via the singular data source so we get metastore_info.region and can
# validate it matches the workspace region (guard below). One of these is active at
# a time: metastore_id override wins; else name; else neither (no binding).
data "databricks_metastore" "by_id" {
  count        = var.metastore_id != "" ? 1 : 0
  provider     = databricks.accounts
  metastore_id = var.metastore_id
}

data "databricks_metastore" "by_name" {
  count    = (var.metastore_id == "" && var.metastore_name != "") ? 1 : 0
  provider = databricks.accounts
  name     = var.metastore_name
}

locals {
  # Precedence: explicit metastore_id > name lookup > "" (no binding).
  resolved_metastore_id = (
    var.metastore_id != "" ? data.databricks_metastore.by_id[0].id :
    var.metastore_name != "" ? data.databricks_metastore.by_name[0].id :
    ""
  )

  # Region of the resolved metastore, whichever path resolved it ("" when none).
  resolved_metastore_region = (
    var.metastore_id != "" ? data.databricks_metastore.by_id[0].metastore_info[0].region :
    var.metastore_name != "" ? data.databricks_metastore.by_name[0].metastore_info[0].region :
    ""
  )

  # Guard: a name OR an ID can point at a metastore in a DIFFERENT region, which
  # would fail the assignment with an opaque API error. Fail fast, clearly, for
  # BOTH paths.
  _assert_metastore_region = (
    local.resolved_metastore_region != "" && local.resolved_metastore_region != var.google_region
  ) ? tobool("metastore '${coalesce(var.metastore_name, var.metastore_id)}' is in region '${local.resolved_metastore_region}', not the workspace region '${var.google_region}' — pick the metastore for this region") : true
}

# Bind the workspace to an existing regional Unity Catalog metastore, when one is
# resolved. Only at RUNNING — assignment needs a live workspace. The metastore is
# created out of band (metastore/); this only assigns THIS workspace to it.
#
# NOTE: do NOT also enable account-level "auto-assign new workspaces" for the
# region if you use this — the two collide (workspace already assigned).
resource "databricks_metastore_assignment" "this" {
  count        = (local.resolved_metastore_id != "" && var.expected_workspace_status == "RUNNING") ? 1 : 0
  provider     = databricks.accounts
  metastore_id = local.resolved_metastore_id
  workspace_id = databricks_mws_workspaces.databricks_workspace.workspace_id
}

