# ------------------------------------------------------------------
# Workspace subnet under the existing VPC + intra-subnet firewall rule.
# Prereq: must exist before the Databricks workspace is created.
# ------------------------------------------------------------------

variable "vpc_project_id" {
  type        = string
  description = "Project that hosts the VPC (workspace project for non-shared VPC, host project for shared VPC)."
}

variable "create_vpc" {
  type        = bool
  default     = false
  description = "Create the VPC (named google_vpc_id) if it does not exist. Default false = use an existing VPC. Not supported with Shared VPC."
}

variable "google_vpc_id" {
  type        = string
  description = "VPC name. If create_vpc = true it is created; otherwise it must already exist."
}

variable "subnet_name" {
  type        = string
  description = "Name for the workspace subnet to create."
}

variable "subnet_cidr" {
  type        = string
  description = "Primary IP range for the workspace subnet, e.g. 10.1.0.0/26."
}

# Optionally create the VPC (custom-subnet mode; no auto-created subnets).
resource "google_compute_network" "vpc" {
  count                   = var.create_vpc ? 1 : 0
  project                 = var.vpc_project_id
  name                    = var.google_vpc_id
  auto_create_subnetworks = false
}

locals {
  # Reference the created VPC when create_vpc = true, else the existing name.
  vpc_network = var.create_vpc ? google_compute_network.vpc[0].id : var.google_vpc_id
}

# Workspace subnet, with Private Google Access enabled.
resource "google_compute_subnetwork" "workspace_subnet" {
  project                  = var.vpc_project_id
  name                     = var.subnet_name
  network                  = local.vpc_network
  region                   = var.google_region
  ip_cidr_range            = var.subnet_cidr
  private_ip_google_access = true
}

# Allow all internal communication between VMs within the workspace subnet
# (mirrors the previously-commented default-allow-internal rule).
resource "google_compute_firewall" "intra_subnet_ingress" {
  name        = "${var.subnet_name}-allow-internal"
  project     = var.vpc_project_id
  network     = local.vpc_network
  description = "Allows all internal communication between VM instances within the workspace subnet"

  direction = "INGRESS"
  priority  = 65534

  source_ranges = [google_compute_subnetwork.workspace_subnet.ip_cidr_range]

  allow {
    protocol = "all"
  }
}

output "subnet_name" {
  description = "Name of the created workspace subnet."
  value       = google_compute_subnetwork.workspace_subnet.name
}

output "subnet_id" {
  description = "Self-link/ID of the created workspace subnet."
  value       = google_compute_subnetwork.workspace_subnet.id
}

output "vpc_name" {
  description = "VPC name (created or existing) the subnet lives in."
  value       = var.google_vpc_id
}
