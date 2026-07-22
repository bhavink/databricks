# ------------------------------------------------------------------
# PSC DNS (post-workspace). Needs the workspace URL, so it lives in the root and
# is ordered after the workspace object is created. Gated on enable_private_access.
#
# These records make the workspace URL and the SCC relay hostname resolve to the
# PSC endpoint internal IPs created in module.prereqs, so private (PSC) clients
# reach the workspace over Private Service Connect.
# ------------------------------------------------------------------

locals {
  # Workspace hostname without the scheme, e.g. "1234567890.3.gcp.databricks.com".
  workspace_host = replace(databricks_mws_workspaces.databricks_workspace.workspace_url, "https://", "")
}

# Private zone for gcp.databricks.com, bound to the workspace VPC.
resource "google_dns_managed_zone" "databricks_psc" {
  count      = var.enable_private_access ? 1 : 0
  project    = var.google_project_id
  name       = "${var.databricks_workspace_name}-psc-dbx"
  dns_name   = "gcp.databricks.com."
  visibility = "private"

  private_visibility_config {
    networks {
      network_url = module.prereqs.vpc_self_link
    }
  }
}

# Workspace front-end URL -> plproxy PSC endpoint IP.
resource "google_dns_record_set" "workspace_a" {
  count        = var.enable_private_access ? 1 : 0
  project      = var.google_project_id
  managed_zone = google_dns_managed_zone.databricks_psc[0].name
  name         = "${local.workspace_host}."
  type         = "A"
  ttl          = 300
  rrdatas      = [module.prereqs.psc_workspace_ip]
}

# Workspace back-end (data plane) hostname -> same plproxy PSC endpoint IP.
resource "google_dns_record_set" "workspace_dp_a" {
  count        = var.enable_private_access ? 1 : 0
  project      = var.google_project_id
  managed_zone = google_dns_managed_zone.databricks_psc[0].name
  name         = "dp-${local.workspace_host}."
  type         = "A"
  ttl          = 300
  rrdatas      = [module.prereqs.psc_workspace_ip]
}

# SCC relay hostname (regional) -> ngrok relay PSC endpoint IP.
resource "google_dns_record_set" "relay_a" {
  count        = var.enable_private_access ? 1 : 0
  project      = var.google_project_id
  managed_zone = google_dns_managed_zone.databricks_psc[0].name
  name         = "tunnel.${var.google_region}.gcp.databricks.com."
  type         = "A"
  ttl          = 300
  rrdatas      = [module.prereqs.psc_relay_ip]
}

# Front-end PSC auth hostname (regional) -> workspace (plproxy) PSC endpoint IP.
# Required for the front-end private auth path, resolves to the same front-end IP.
resource "google_dns_record_set" "psc_auth_a" {
  count        = var.enable_private_access ? 1 : 0
  project      = var.google_project_id
  managed_zone = google_dns_managed_zone.databricks_psc[0].name
  name         = "${var.google_region}.psc-auth.gcp.databricks.com."
  type         = "A"
  ttl          = 300
  rrdatas      = [module.prereqs.psc_workspace_ip]
}
