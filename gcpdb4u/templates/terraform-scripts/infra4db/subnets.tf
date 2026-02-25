# Check if subnets exist
data "google_compute_subnetwork" "existing_subnets" {
  for_each = var.subnet_configs
  name     = each.key
  region   = each.value.region
  project  = var.vpc_project_id
}

resource "google_compute_subnetwork" "subnets" {
  for_each                 = var.subnet_configs
  name                     = "subnet-${each.key}"
  network                  = google_compute_network.vpc.id
  region                   = each.value.region
  ip_cidr_range            = each.value.cidr
  private_ip_google_access = true

  lifecycle {
    # Prevent destruction if the subnet already exists
    # prevent_destroy = true
  }
}

# Add PSC subnets using the provided CIDR ranges from psc_subnet_configs variable
resource "google_compute_subnetwork" "psc_subnets" {
  for_each = var.create_psc_resources ? var.psc_subnet_configs : {}

  name          = "psc-subnet-${each.key}" # Unique name per region
  ip_cidr_range = each.value.cidr          # Use the CIDR range provided in the variable
  region        = each.value.region        # Use the region from the variable
  network       = google_compute_network.vpc.id
}
