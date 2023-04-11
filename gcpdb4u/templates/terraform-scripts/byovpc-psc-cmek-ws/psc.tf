***REMOVED*** PSC endpoints creation
***REMOVED*** Make sure that the endpoints are created before you create the workspace

resource "google_compute_forwarding_rule" "backend_psc_ep" {
  depends_on = [
    google_compute_address.backend_pe_ip_address
  ]
  region      = var.google_region
  project     = var.google_shared_vpc_project
  name        = var.relay_pe
  network     = var.google_vpc_id
  ip_address  = google_compute_address.backend_pe_ip_address.id
  target      = var.relay_service_attachment
  load_balancing_scheme = "" ***REMOVED***This field must be set to "" if the target is an URI of a service attachment. Default value is EXTERNAL
}

resource "google_compute_address" "backend_pe_ip_address" {
  name         = var.relay_pe_ip_name
  provider     = google-beta
  project      = var.google_shared_vpc_project
  region       = var.google_region
  subnetwork   = var.google_pe_subnet
  address_type = "INTERNAL"
}

resource "google_compute_forwarding_rule" "frontend_psc_ep" {
  depends_on = [
    google_compute_address.frontend_pe_ip_address
  ]
  region      = var.google_region
  name        = var.workspace_pe
  project     = var.google_shared_vpc_project
  network     = var.google_vpc_id
  ip_address  = google_compute_address.frontend_pe_ip_address.id
  target      = var.workspace_service_attachment
  load_balancing_scheme = "" ***REMOVED***This field must be set to "" if the target is an URI of a service attachment. Default value is EXTERNAL
}

resource "google_compute_address" "frontend_pe_ip_address" {
  name         = var.workspace_pe_ip_name
  provider     = google-beta
  project      = var.google_shared_vpc_project
  region       = var.google_region
  subnetwork   = var.google_pe_subnet
  address_type = "INTERNAL"
}

output "front_end_psc_status"{
  value = "Frontend psc status: ${google_compute_forwarding_rule.frontend_psc_ep.psc_connection_status}"
}

output "backend_end_psc_status"{
  value = "Backend psc status: ${google_compute_forwarding_rule.backend_psc_ep.psc_connection_status}"
}