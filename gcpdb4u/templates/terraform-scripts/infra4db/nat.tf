# Check if routers exist
data "google_compute_router" "existing_routers" {
  for_each = var.subnet_configs
  name     = "router-${each.key}"
  region   = each.value.region
  project  = var.vpc_project_id
  network  = google_compute_network.vpc.name
}

resource "google_compute_router" "routers" {
  for_each = var.subnet_configs
  name     = "router-${each.key}"
  network  = google_compute_network.vpc.id
  region   = each.value.region

  lifecycle {
    # Prevent destruction if the router already exists
    # prevent_destroy = true
  }
}

# Check if NATs exist
data "google_compute_router_nat" "existing_nats" {
  for_each = var.subnet_configs
  name     = "nat-${each.key}"
  router   = google_compute_router.routers[each.key].name
  region   = each.value.region
  project  = var.vpc_project_id
}

resource "google_compute_router_nat" "nats" {
  for_each                           = var.subnet_configs
  name                               = "nat-${each.key}"
  router                             = google_compute_router.routers[each.key].name
  region                             = each.value.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  lifecycle {
    # Prevent destruction if the NAT already exists
    # prevent_destroy = true
  }
} 