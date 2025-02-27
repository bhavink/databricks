# Allow internal ingress traffic between Databricks tagged instances - one rule per source subnet
resource "google_compute_firewall" "databricks_internal_ingress" {
  for_each = var.subnet_configs  # Create one rule per source subnet
  name          = "allow-databricks-internal-ingress-${each.key}"  # Unique name for each rule
  network       = google_compute_network.vpc.name
  direction = "INGRESS"
  source_ranges = [
    each.value.cidr  # Use the CIDR of the current subnet
  ]
  
  allow {
    protocol = "all"
  }

  destination_ranges = [
    each.value.cidr  # Use the CIDR of the current subnet
  ]
}

# Allow internal egress traffic between Databricks tagged instances - one rule per source subnet
resource "google_compute_firewall" "databricks_internal_egress" {
  for_each = var.subnet_configs  # Create one rule per source subnet
  name          = "allow-databricks-internal-egress-${each.key}"  # Unique name for each rule
  network       = google_compute_network.vpc.name
  direction = "EGRESS"
  destination_ranges = [
    each.value.cidr  # Use the CIDR of the current subnet
  ]
  
  allow {
    protocol = "all"
  }

  source_ranges = [
    each.value.cidr  # Use the CIDR of the current subnet
  ]
}

# Allow egress to specific IPs over port 443 for each regional non-PSC subnet
resource "google_compute_firewall" "allow_specific_egress" {
  for_each = var.create_psc_resources ? { for k, v in var.subnet_configs : k => v if !v.psc } : {}  # Filter for non-PSC subnets

  name    = "allow-egress-to-databricks-controlplane-ips-${each.key}"  # Unique name for each rule
  network = google_compute_network.vpc.name
  direction = "EGRESS"

  allow {
    protocol = "tcp"
    ports    = ["443"]
  }

  source_ranges = [
    each.value.cidr  # Use the CIDR of the current non-PSC subnet
  ]

  destination_ranges = split(", ", lookup(var.destination_ips, each.value.region))  # Use the variable for destination IPs
}

# Deny egress traffic for all subnets with priority 1100
resource "google_compute_firewall" "deny_egress_all" {
  name    = "deny-egress-all"
  network = google_compute_network.vpc.name
  direction = "EGRESS"
  priority = 1100

  # Deny all egress traffic
  deny {
    protocol = "all"
  }
}

# Allow egress from non-PSC subnets to PSC subnets - one rule per region
resource "google_compute_firewall" "allow_egress_to_psc" {
  for_each = var.create_psc_resources ? { for k, v in var.psc_subnet_configs : k => v } : {}  # Use psc_subnet_configs

  name    = "databricks-psc-egress-${each.value.region}"  # Unique name for each rule
  network = google_compute_network.vpc.id
  
  source_ranges = [
    google_compute_subnetwork.subnets[each.key].ip_cidr_range  # Use the CIDR of the current non-PSC subnet
  ]

  destination_ranges = [
    each.value.cidr  # Target the corresponding PSC subnet from psc_subnet_configs
  ]

  allow {
    protocol = "all"  # Allow all protocols
  }

  direction = "EGRESS"
}

resource "google_compute_firewall" "allow_egress_to_private_googleapis" {
  name    = "egress-to-private-googleapi-ips"
  network = google_compute_network.vpc.id  # Replace with your actual VPC

  direction         = "EGRESS"
  source_ranges     = [for s in var.subnet_configs : s.cidr]  # Collects all subnet CIDRs
  destination_ranges = var.private_googleapi_ips  # Uses the list of destination IPs

  allow {
    protocol = "all"
  }

  priority = 1000
}


resource "google_compute_firewall" "allow_egress_to_databricks_hive" {
  for_each = var.subnet_configs  # Loop through available subnets

  name    = "egress-to-databricks-hive-${each.value.region}"  # Unique rule name per region
  network = google_compute_network.vpc.id         # Reference your VPC

  direction = "EGRESS"

  source_ranges = [each.value.cidr]  # Get CIDR of the current subnet

  destination_ranges = lookup(var.databricks_hive_ips, each.value.region, null) != null ? [lookup(var.databricks_hive_ips, each.value.region)] : [] # Select destination IP based on region

  allow {
   protocol = "all"
  }
  priority = 1000
}


   

  