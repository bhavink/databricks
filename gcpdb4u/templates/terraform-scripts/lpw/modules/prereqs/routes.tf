# ------------------------------------------------------------------
# Egress route for the PSC / Private Google Access path (pre-workspace).
# Only created alongside a NEW VPC — an existing VPC already has its own default
# route, and adding a duplicate-named one would conflict. Gated on
# enable_private_access AND create_vpc.
# ------------------------------------------------------------------
resource "google_compute_route" "default_internet_gateway" {
  count            = var.enable_private_access && var.create_vpc ? 1 : 0
  project          = var.vpc_project_id
  name             = "${var.subnet_name}-default-igw"
  dest_range       = "0.0.0.0/0"
  network          = local.vpc_network
  next_hop_gateway = "default-internet-gateway"
  priority         = 1000
}
