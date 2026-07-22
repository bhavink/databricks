# ------------------------------------------------------------------
# Private Service Connect (PSC) prereqs. Created BEFORE the workspace when
# enable_private_access = true. Nothing here depends on the workspace GSA.
#
#   - PSC endpoint subnet (hosts the two internal PSC IPs)
#   - two internal IPs: workspace (plproxy) + SCC relay (ngrok)
#   - two consumer endpoints (forwarding rules) -> Databricks service attachments
#
# The DNS records that map the workspace URL / relay hostname to these IPs are
# created in the ROOT (dns.tf) because they need the workspace URL, which only
# exists after the workspace object is created.
# ------------------------------------------------------------------

variable "enable_private_access" {
  type        = bool
  default     = false
  description = "Create PSC subnet + endpoints (root then creates the PSC DNS). Off = standard public workspace, no PSC resources."
}

variable "psc_subnet_cidr" {
  type        = string
  default     = ""
  description = "CIDR for the PSC endpoint subnet (separate from the workspace subnet), e.g. 10.1.255.0/26. Required when enable_private_access = true."
}

variable "workspace_service_attachment" {
  type        = string
  default     = ""
  description = "Databricks workspace (plproxy) PSC service attachment URI for the region. Required when enable_private_access = true."
}

variable "relay_service_attachment" {
  type        = string
  default     = ""
  description = "Databricks SCC relay (ngrok) PSC service attachment URI for the region. Required when enable_private_access = true."
}

# Dedicated subnet to host the two PSC endpoint internal IPs.
resource "google_compute_subnetwork" "psc_subnet" {
  count         = var.enable_private_access ? 1 : 0
  project       = var.vpc_project_id
  name          = "${var.subnet_name}-psc"
  network       = local.vpc_network
  region        = var.google_region
  ip_cidr_range = var.psc_subnet_cidr
}

# Internal IP for the workspace front-end/back-end (plproxy) PSC endpoint.
resource "google_compute_address" "workspace_pe_ip" {
  count        = var.enable_private_access ? 1 : 0
  project      = var.vpc_project_id
  name         = "${var.subnet_name}-workspace-pe-ip"
  region       = var.google_region
  subnetwork   = google_compute_subnetwork.psc_subnet[0].id
  address_type = "INTERNAL"
}

# Internal IP for the SCC relay (ngrok) PSC endpoint.
resource "google_compute_address" "relay_pe_ip" {
  count        = var.enable_private_access ? 1 : 0
  project      = var.vpc_project_id
  name         = "${var.subnet_name}-relay-pe-ip"
  region       = var.google_region
  subnetwork   = google_compute_subnetwork.psc_subnet[0].id
  address_type = "INTERNAL"
}

# Consumer PSC endpoint -> Databricks workspace service attachment (plproxy).
resource "google_compute_forwarding_rule" "workspace_psc_ep" {
  count                 = var.enable_private_access ? 1 : 0
  project               = var.vpc_project_id
  region                = var.google_region
  name                  = "${var.subnet_name}-workspace-psc-ep"
  network               = local.vpc_network
  subnetwork            = google_compute_subnetwork.psc_subnet[0].id
  ip_address            = google_compute_address.workspace_pe_ip[0].id
  target                = var.workspace_service_attachment
  load_balancing_scheme = "" # must be "" when target is a service attachment URI
}

# Consumer PSC endpoint -> Databricks SCC relay service attachment (ngrok).
resource "google_compute_forwarding_rule" "relay_psc_ep" {
  count                 = var.enable_private_access ? 1 : 0
  project               = var.vpc_project_id
  region                = var.google_region
  name                  = "${var.subnet_name}-relay-psc-ep"
  network               = local.vpc_network
  subnetwork            = google_compute_subnetwork.psc_subnet[0].id
  ip_address            = google_compute_address.relay_pe_ip[0].id
  target                = var.relay_service_attachment
  load_balancing_scheme = ""
}

output "psc_workspace_ip" {
  description = "Internal IP of the workspace (plproxy) PSC endpoint. Null when private access is off."
  value       = var.enable_private_access ? google_compute_address.workspace_pe_ip[0].address : null
}

output "psc_relay_ip" {
  description = "Internal IP of the SCC relay (ngrok) PSC endpoint. Null when private access is off."
  value       = var.enable_private_access ? google_compute_address.relay_pe_ip[0].address : null
}

# Forwarding-rule names = the psc_endpoint_name that databricks_mws_vpc_endpoint
# registers on the Databricks side.
output "psc_workspace_ep_name" {
  description = "Name of the workspace (plproxy) PSC forwarding rule. Null when private access is off."
  value       = var.enable_private_access ? google_compute_forwarding_rule.workspace_psc_ep[0].name : null
}

output "psc_relay_ep_name" {
  description = "Name of the SCC relay (ngrok) PSC forwarding rule. Null when private access is off."
  value       = var.enable_private_access ? google_compute_forwarding_rule.relay_psc_ep[0].name : null
}

output "vpc_self_link" {
  description = "Network URL for DNS private-zone binding. Works for a created or an existing VPC."
  value       = var.create_vpc ? google_compute_network.vpc[0].id : "projects/${var.vpc_project_id}/global/networks/${var.google_vpc_id}"
}
