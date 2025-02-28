***REMOVED*** Make sure to NOT create a private DNS zone for a non PSC databricks workspace
***REMOVED*** Do not use same vpc for PSC and non-PSC workspaces as the private DNS zone attached to the
***REMOVED*** vpc used by these workpsaces would render non PSC workspace broken
***REMOVED*** It is a good practice to keep such workspaces in a separate vpc, you could still use sme project though
resource "google_dns_managed_zone" "private_databricks" {
  count = var.create_psc_resources ? 1 : 0  ***REMOVED*** Create only if create_psc_resources = true

  name        = "private-databricks"
  dns_name    = "gcp.databricks.com."
  visibility  = "private"
  
  private_visibility_config {
    networks {
      network_url = google_compute_network.vpc.id
    }
  }
}


***REMOVED*** Private DNS zone for googleapis.com
resource "google_dns_managed_zone" "private_googleapis" {
  name        = "private-googleapis"
  dns_name    = "googleapis.com."
  visibility  = "private"
  
  private_visibility_config {
    networks {
      network_url = google_compute_network.vpc.id
    }
  }
}

***REMOVED*** A records for private.googleapis.com
resource "google_dns_record_set" "private_googleapis_a" {
  name         = "private.googleapis.com."
  managed_zone = google_dns_managed_zone.private_googleapis.name
  type         = "A"
  ttl          = 300
  rrdatas      = ["199.36.153.8", "199.36.153.9", "199.36.153.10", "199.36.153.11"]
}

***REMOVED*** CNAME record for *.googleapis.com
resource "google_dns_record_set" "private_googleapis_cname" {
  name         = "*.googleapis.com."
  managed_zone = google_dns_managed_zone.private_googleapis.name
  type         = "CNAME"
  ttl          = 300
  rrdatas      = ["private.googleapis.com."]
}

***REMOVED*** A records for restricted.googleapis.com
resource "google_dns_record_set" "restricted_googleapis_a" {
  name         = "restricted.googleapis.com."
  managed_zone = google_dns_managed_zone.private_googleapis.name
  type         = "A"
  ttl          = 300
  rrdatas      = ["199.36.153.4", "199.36.153.5", "199.36.153.6", "199.36.153.7"]
}