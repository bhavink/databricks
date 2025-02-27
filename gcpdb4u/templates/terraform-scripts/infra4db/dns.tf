# This is required if you were to use Private Google Access which I would highly recommend
resource "google_dns_managed_zone" "private_databricks" {
  count = var.create_psc_resources ? 1 : 0  # Create only if create_psc_resources = true

  name        = "private-databricks"
  dns_name    = "gcp.databricks.com."
  visibility  = "private"
  
  private_visibility_config {
    networks {
      network_url = google_compute_network.vpc.id
    }
  }
}


# Private DNS zone for googleapis.com
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

# A records for private.googleapis.com
resource "google_dns_record_set" "private_googleapis_a" {
  name         = "private.googleapis.com."
  managed_zone = google_dns_managed_zone.private_googleapis.name
  type         = "A"
  ttl          = 300
  rrdatas      = ["199.36.153.8", "199.36.153.9", "199.36.153.10", "199.36.153.11"]
}

# CNAME record for *.googleapis.com
resource "google_dns_record_set" "private_googleapis_cname" {
  name         = "*.googleapis.com."
  managed_zone = google_dns_managed_zone.private_googleapis.name
  type         = "CNAME"
  ttl          = 300
  rrdatas      = ["private.googleapis.com."]
}

# A records for restricted.googleapis.com
resource "google_dns_record_set" "restricted_googleapis_a" {
  name         = "restricted.googleapis.com."
  managed_zone = google_dns_managed_zone.private_googleapis.name
  type         = "A"
  ttl          = 300
  rrdatas      = ["199.36.153.4", "199.36.153.5", "199.36.153.6", "199.36.153.7"]
}