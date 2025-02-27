resource "google_compute_route" "default_internet_gateway" {
  name             = "default-internet-gateway"
  dest_range       = "0.0.0.0/0"
  network          = google_compute_network.vpc.id
  next_hop_gateway = "default-internet-gateway"
  priority         = 1000
} 