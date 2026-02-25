# Check if VPC exists
data "google_compute_network" "existing_vpc" {
  name    = var.network_name
  project = var.vpc_project_id
  count   = 0
}

resource "google_compute_network" "vpc" {
  name                    = var.network_name
  auto_create_subnetworks = false
  project                 = var.vpc_project_id
} 