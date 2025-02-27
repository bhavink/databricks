***REMOVED*** PSC endpoints creation based on create_psc_endpoints variable
resource "google_compute_address" "relay_pe_ip_address" {
  for_each = var.create_psc_resources ? var.psc_attachments : {}

  name         = "${each.key}-relay-pe-ip"  ***REMOVED*** Unique name per region
  provider     = google-beta
  project      = var.vpc_project_id  ***REMOVED*** Updated to use project_id
  region       = each.key
  subnetwork   = google_compute_subnetwork.psc_subnets[each.key].id  ***REMOVED*** Reference the PSC subnet
  address_type = "INTERNAL"
}

resource "google_compute_forwarding_rule" "relay_psc_ep" {
  for_each = var.create_psc_resources ? var.psc_attachments : {}

  depends_on = [
    google_compute_address.relay_pe_ip_address  ***REMOVED*** Reference the specific address
  ]
  region      = each.key
  project     = var.vpc_project_id  ***REMOVED*** Updated to use project_id
  name        = "${each.key}-relay-psc-ep"  ***REMOVED*** Unique name per region
  network     = google_compute_network.vpc.id  ***REMOVED*** Reference to the VPC being created
  subnetwork = google_compute_subnetwork.psc_subnets[each.key].id
  ip_address  = google_compute_address.relay_pe_ip_address[each.key].id
  target      = var.psc_attachments[each.key].relay_attachment
  load_balancing_scheme = "" ***REMOVED*** This field must be set to "" if the target is an URI of a service attachment. Default value is EXTERNAL
}

resource "google_compute_address" "workspace_pe_ip_address" {
  for_each = var.create_psc_resources ? var.psc_attachments : {}

  name         = "${each.key}-workspace-pe-ip"  ***REMOVED*** Unique name per region
  provider     = google-beta
  project      = var.vpc_project_id  ***REMOVED*** Updated to use project_id
  region       = each.key
  subnetwork   = google_compute_subnetwork.psc_subnets[each.key].id  ***REMOVED*** Reference the PSC subnet
  address_type = "INTERNAL"
}

resource "google_compute_forwarding_rule" "workspace_psc_ep" {
  for_each = var.create_psc_resources ? var.psc_attachments : {}

  depends_on = [
    google_compute_address.workspace_pe_ip_address  ***REMOVED*** Reference the specific address
  ]
  region      = each.key
  project     = var.vpc_project_id  ***REMOVED*** Updated to use project_id
  name        = "${each.key}-workspace-psc-ep"  ***REMOVED*** Unique name per region
  network     = google_compute_network.vpc.id  ***REMOVED*** Reference to the VPC being created
  subnetwork = google_compute_subnetwork.psc_subnets[each.key].id
  ip_address  = google_compute_address.workspace_pe_ip_address[each.key].id
  target      = var.psc_attachments[each.key].workspace_attachment
  load_balancing_scheme = "" ***REMOVED*** This field must be set to "" if the target is an URI of a service attachment. Default value is EXTERNAL
}

