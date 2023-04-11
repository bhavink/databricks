***REMOVED*** Create private zone for "databricks" only after the workspace is successfully created

variable private_zone_name {}
variable dns_name {}

resource "google_dns_managed_zone" "databricks-private-zone" {
  depends_on = [ databricks_mws_workspaces.databricks_workspace ]
  provider = google.vpc_project
  name        = var.private_zone_name
  dns_name    = var.dns_name
  description = "Databricks private DNS zone"
  visibility = "private"
  private_visibility_config {
    networks {
      network_url = "https://www.googleapis.com/compute/v1/projects/${var.google_shared_vpc_project}/global/networks/${var.google_vpc_id}"
    }
  }
}

locals {
   workspace_id = regex("[0-9]+\\.[0-9]+", databricks_mws_workspaces.databricks_workspace.workspace_url) 
}

output "extracted_value" {
  value = "workspace id: ${local.workspace_id}"
}

/* 
Add A records for backend and frontend private endpoints

There are 2 sets of A records:
- Per region and Per workspace

Per region A records includes:
- tunnel.<gcp_region>.gcp.databricks.com. which resolves to backend pe ip ex: tunnel.us-central1.gcp.databricks.com.
- <gcp_region>.psc-auth.gcp.databricks.com. which resolves to frontend pe ip ex: us-central1.psc-auth.gcp.databricks.com.
If you were to create more than one workspace in a given gcp_region 
then the above mentioned A records would shared by all the workspaces in that region

Per workspace A records includes:
- dp-<workspace_id>.gcp.databricks.com. which resolves to frontend pe ip ex: dp-8296020533331897.7.gcp.databricks.com.
- <workspace_id>.gcp.databricks.com. which resolves to frontend pe ip ex: 8296020533331897.7.gcp.databricks.com.

Summary
- In short you'll have at minimum 4 DNS A records per workspace, 3 resolving to frontend private endpoint and 1 to backend private endpoint
- You can share same frontend and backend private endpoints with multiple workspaces in the same region.

*/

resource "google_dns_record_set" "record_set_workspace_url" {
  depends_on = [ databricks_mws_workspaces.databricks_workspace ]
  provider = google.vpc_project
  managed_zone = google_dns_managed_zone.databricks-private-zone.name
  name         = "${local.workspace_id}.${google_dns_managed_zone.databricks-private-zone.dns_name}"
  type         = "A"
  ttl          = 300


  rrdatas = [
    "${google_compute_address.frontend_pe_ip_address.address}"
  ]

  

}
resource "google_dns_record_set" "record_set_workspace_psc_auth" {
  depends_on = [ databricks_mws_workspaces.databricks_workspace ]
  provider = google.vpc_project
  managed_zone = google_dns_managed_zone.databricks-private-zone.name
  name         = "${var.google_region}.psc-auth.${google_dns_managed_zone.databricks-private-zone.dns_name}"
  type         = "A"
  ttl          = 300


  rrdatas = [
    "${google_compute_address.frontend_pe_ip_address.address}"
  ]

}

resource "google_dns_record_set" "record_set_workspace_dp" {
  depends_on = [ databricks_mws_workspaces.databricks_workspace ]
  provider = google.vpc_project
  managed_zone = google_dns_managed_zone.databricks-private-zone.name
  name         = "dp-${local.workspace_id}.${google_dns_managed_zone.databricks-private-zone.dns_name}"
  type         = "A"
  ttl          = 300


  rrdatas = [
    "${google_compute_address.frontend_pe_ip_address.address}"
  ]

}


resource "google_dns_record_set" "record_set_relay" {
  depends_on = [ databricks_mws_workspaces.databricks_workspace ]
  provider = google.vpc_project
  managed_zone = google_dns_managed_zone.databricks-private-zone.name
  name         = "tunnel.${var.google_region}.${google_dns_managed_zone.databricks-private-zone.dns_name}"
  type         = "A"
  ttl          = 300


  rrdatas = [
    "${google_compute_address.backend_pe_ip_address.address}"
  ]

}