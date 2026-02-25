/*
Databricks GCP DNS Setup - Extended Configuration
=================================================

This configuration creates DNS zones and records for Databricks workspaces on GCP.
Supports both Private Service Connect (PSC) and Non-PSC workspace deployments.

Documentation: See DNS-Setup-Guide.md in the gcpdb4u directory

PSC Workspaces:
- 4 private DNS zones with CNAME and A records
- Resolves to private IPs within VPC
- No public internet exposure

Non-PSC Workspaces:
- Regional forwarding zones
- Forwards to Google Public DNS (8.8.8.8, 8.8.4.4)
- Resolves to public IPs

Common:
- Accounts console forwarding zone (required for both types)
*/

# ============================================
# VARIABLES
# ============================================

variable "workspace_type" {
  description = "Type of Databricks workspace deployment: 'psc' or 'non-psc'"
  type        = string
  validation {
    condition     = contains(["psc", "non-psc"], var.workspace_type)
    error_message = "workspace_type must be either 'psc' or 'non-psc'."
  }
}

variable "databricks_regions" {
  description = <<-EOT
    Map of regions for Databricks deployment.
    For PSC workspaces, include frontend_pe_ip and backend_pe_ip.
    For Non-PSC workspaces, IPs are not required.
  EOT
  type = map(object({
    region         = string
    frontend_pe_ip = optional(string, "") # Required for PSC workspaces
    backend_pe_ip  = optional(string, "") # Required for PSC workspaces
  }))

  validation {
    condition     = length(var.databricks_regions) > 0
    error_message = "At least one region must be specified in databricks_regions."
  }
}

variable "vpc_network_id" {
  description = "VPC network ID for private DNS zones (format: projects/PROJECT_ID/global/networks/VPC_NAME)"
  type        = string
}

variable "vpc_project_id" {
  description = "GCP Project ID where the VPC network resides"
  type        = string
}

variable "workspaces" {
  description = <<-EOT
    Map of workspace configurations for PSC deployments.
    Each workspace needs workspace_id and region for CNAME record creation.
    Leave empty for Non-PSC workspaces.
  EOT
  type = map(object({
    workspace_id = string # Example: "311716749948597.7"
    region       = string # Must match a key in databricks_regions
  }))
  default = {}
}

# ============================================
# PSC WORKSPACE DNS CONFIGURATION
# ============================================

# Zone 1: Main Frontend Zone - gcp.databricks.com
# Contains CNAME records for workspace URLs
resource "google_dns_managed_zone" "databricks_main" {
  count       = var.workspace_type == "psc" ? 1 : 0
  name        = "databricks-main"
  dns_name    = "gcp.databricks.com."
  description = "Private DNS zone for Databricks workspace frontend URLs (PSC)"
  visibility  = "private"

  private_visibility_config {
    networks {
      network_url = var.vpc_network_id
    }
  }

  labels = {
    purpose    = "databricks-dns"
    zone_type  = "psc-main"
    managed_by = "terraform"
  }
}

# CNAME Records: workspace_id.gcp.databricks.com → region.psc.gcp.databricks.com
# Each workspace gets a CNAME pointing to the intermediate PSC zone
resource "google_dns_record_set" "workspace_cname" {
  for_each = var.workspace_type == "psc" ? var.workspaces : {}

  managed_zone = google_dns_managed_zone.databricks_main[0].name
  name         = "${each.value.workspace_id}.${google_dns_managed_zone.databricks_main[0].dns_name}"
  type         = "CNAME"
  ttl          = 300
  rrdatas      = ["${each.value.region}.psc.${google_dns_managed_zone.databricks_main[0].dns_name}"]
}

# Zone 2: Intermediate Frontend Zone - psc.gcp.databricks.com
# Contains A records mapping region to frontend private IP
resource "google_dns_managed_zone" "databricks_psc_webapp" {
  count       = var.workspace_type == "psc" ? 1 : 0
  name        = "databricks-psc-webapp"
  dns_name    = "psc.gcp.databricks.com."
  description = "Private DNS zone for PSC webapp intermediate records"
  visibility  = "private"

  private_visibility_config {
    networks {
      network_url = var.vpc_network_id
    }
  }

  labels = {
    purpose    = "databricks-dns"
    zone_type  = "psc-intermediate"
    managed_by = "terraform"
  }
}

# A Records: region.psc.gcp.databricks.com → Frontend Private IP
# Maps regional workspace access to frontend PSC endpoint
resource "google_dns_record_set" "psc_webapp_a_record" {
  for_each = var.workspace_type == "psc" ? var.databricks_regions : {}

  managed_zone = google_dns_managed_zone.databricks_psc_webapp[0].name
  name         = "${each.key}.${google_dns_managed_zone.databricks_psc_webapp[0].dns_name}"
  type         = "A"
  ttl          = 300
  rrdatas      = [each.value.frontend_pe_ip]

  depends_on = [google_dns_managed_zone.databricks_psc_webapp]
}

# Zone 3: Auth Callback Zone - psc-auth.gcp.databricks.com
# Contains A records for authentication service
resource "google_dns_managed_zone" "databricks_psc_auth" {
  count       = var.workspace_type == "psc" ? 1 : 0
  name        = "databricks-psc-webapp-auth"
  dns_name    = "psc-auth.gcp.databricks.com."
  description = "Private DNS zone for PSC authentication callback"
  visibility  = "private"

  private_visibility_config {
    networks {
      network_url = var.vpc_network_id
    }
  }

  labels = {
    purpose    = "databricks-dns"
    zone_type  = "psc-auth"
    managed_by = "terraform"
  }
}

# A Records: region.psc-auth.gcp.databricks.com → Frontend Private IP
# Maps regional auth callbacks to frontend PSC endpoint (same IP as webapp)
resource "google_dns_record_set" "psc_auth_a_record" {
  for_each = var.workspace_type == "psc" ? var.databricks_regions : {}

  managed_zone = google_dns_managed_zone.databricks_psc_auth[0].name
  name         = "${each.key}.${google_dns_managed_zone.databricks_psc_auth[0].dns_name}"
  type         = "A"
  ttl          = 300
  rrdatas      = [each.value.frontend_pe_ip]

  depends_on = [google_dns_managed_zone.databricks_psc_auth]
}

# Zone 4: Backend/Tunnel Zone - tunnel.<region>.gcp.databricks.com
# One zone per region for compute-to-control plane communication
resource "google_dns_managed_zone" "databricks_psc_backend" {
  for_each = var.workspace_type == "psc" ? var.databricks_regions : {}

  name        = "databricks-psc-backend-${each.key}"
  dns_name    = "tunnel.${each.key}.gcp.databricks.com."
  description = "Private DNS zone for PSC backend tunnel in ${each.key}"
  visibility  = "private"

  private_visibility_config {
    networks {
      network_url = var.vpc_network_id
    }
  }

  labels = {
    purpose    = "databricks-dns"
    zone_type  = "psc-backend"
    region     = each.key
    managed_by = "terraform"
  }
}

# A Record: tunnel.region.gcp.databricks.com → Backend Private IP
# Maps tunnel DNS to backend PSC endpoint for compute clusters
resource "google_dns_record_set" "psc_backend_a_record" {
  for_each = var.workspace_type == "psc" ? var.databricks_regions : {}

  managed_zone = google_dns_managed_zone.databricks_psc_backend[each.key].name
  name         = google_dns_managed_zone.databricks_psc_backend[each.key].dns_name
  type         = "A"
  ttl          = 300
  rrdatas      = [each.value.backend_pe_ip]

  depends_on = [google_dns_managed_zone.databricks_psc_backend]
}

# ============================================
# NON-PSC WORKSPACE DNS CONFIGURATION
# ============================================

# Regional Forwarding Zones - region.gcp.databricks.com
# Forwards DNS queries to Google Public DNS for public IP resolution
resource "google_dns_managed_zone" "databricks_public_regional" {
  for_each = var.workspace_type == "non-psc" ? var.databricks_regions : {}

  name        = "databricks-public-${each.key}"
  dns_name    = "${each.key}.gcp.databricks.com."
  description = "Forwarding DNS zone for Non-PSC Databricks workspaces in ${each.key}"
  visibility  = "private"

  private_visibility_config {
    networks {
      network_url = var.vpc_network_id
    }
  }

  forwarding_config {
    target_name_servers {
      ipv4_address = "8.8.8.8" # Google Public DNS
    }
    target_name_servers {
      ipv4_address = "8.8.4.4" # Google Public DNS
    }
  }

  labels = {
    purpose    = "databricks-dns"
    zone_type  = "non-psc-forwarding"
    region     = each.key
    managed_by = "terraform"
  }
}

# ============================================
# COMMON: ACCOUNTS CONSOLE (BOTH WORKSPACE TYPES)
# ============================================

# Accounts Console Forwarding Zone - accounts.gcp.databricks.com
# Required for both PSC and Non-PSC workspaces to access Databricks Accounts Console
resource "google_dns_managed_zone" "databricks_accounts" {
  name        = "databricks-account-console"
  dns_name    = "accounts.gcp.databricks.com."
  description = "Forwarding DNS zone for Databricks Accounts Console (required for all workspace types)"
  visibility  = "private"

  private_visibility_config {
    networks {
      network_url = var.vpc_network_id
    }
  }

  forwarding_config {
    target_name_servers {
      ipv4_address = "8.8.8.8" # Google Public DNS
    }
    target_name_servers {
      ipv4_address = "8.8.4.4" # Google Public DNS
    }
  }

  labels = {
    purpose    = "databricks-dns"
    zone_type  = "accounts-console"
    managed_by = "terraform"
  }
}

# ============================================
# OUTPUTS
# ============================================

output "dns_zones_created" {
  description = "Summary of DNS zones created"
  value = {
    workspace_type = var.workspace_type
    psc_zones = var.workspace_type == "psc" ? {
      main_zone       = try(google_dns_managed_zone.databricks_main[0].name, null)
      psc_webapp_zone = try(google_dns_managed_zone.databricks_psc_webapp[0].name, null)
      psc_auth_zone   = try(google_dns_managed_zone.databricks_psc_auth[0].name, null)
      backend_zones   = [for zone in google_dns_managed_zone.databricks_psc_backend : zone.name]
    } : null
    non_psc_zones = var.workspace_type == "non-psc" ? {
      regional_zones = [for zone in google_dns_managed_zone.databricks_public_regional : zone.name]
    } : null
    accounts_zone = google_dns_managed_zone.databricks_accounts.name
  }
}

output "dns_zone_details" {
  description = "Detailed information about created DNS zones"
  value = {
    # PSC Zone Details
    psc_main_zone = var.workspace_type == "psc" ? {
      id        = try(google_dns_managed_zone.databricks_main[0].id, null)
      dns_name  = try(google_dns_managed_zone.databricks_main[0].dns_name, null)
      zone_name = try(google_dns_managed_zone.databricks_main[0].name, null)
    } : null

    psc_webapp_zone = var.workspace_type == "psc" ? {
      id        = try(google_dns_managed_zone.databricks_psc_webapp[0].id, null)
      dns_name  = try(google_dns_managed_zone.databricks_psc_webapp[0].dns_name, null)
      zone_name = try(google_dns_managed_zone.databricks_psc_webapp[0].name, null)
    } : null

    psc_auth_zone = var.workspace_type == "psc" ? {
      id        = try(google_dns_managed_zone.databricks_psc_auth[0].id, null)
      dns_name  = try(google_dns_managed_zone.databricks_psc_auth[0].dns_name, null)
      zone_name = try(google_dns_managed_zone.databricks_psc_auth[0].name, null)
    } : null

    psc_backend_zones = var.workspace_type == "psc" ? {
      for region, zone in google_dns_managed_zone.databricks_psc_backend : region => {
        id        = zone.id
        dns_name  = zone.dns_name
        zone_name = zone.name
      }
    } : null

    # Non-PSC Zone Details
    non_psc_regional_zones = var.workspace_type == "non-psc" ? {
      for region, zone in google_dns_managed_zone.databricks_public_regional : region => {
        id        = zone.id
        dns_name  = zone.dns_name
        zone_name = zone.name
      }
    } : null

    # Accounts Zone (Common)
    accounts_zone = {
      id        = google_dns_managed_zone.databricks_accounts.id
      dns_name  = google_dns_managed_zone.databricks_accounts.dns_name
      zone_name = google_dns_managed_zone.databricks_accounts.name
    }
  }
}

output "workspace_dns_records" {
  description = "DNS records created for PSC workspaces (CNAME records)"
  value = var.workspace_type == "psc" ? {
    for key, workspace in var.workspaces : key => {
      workspace_id = workspace.workspace_id
      dns_name     = "${workspace.workspace_id}.gcp.databricks.com"
      cname_target = "${workspace.region}.psc.gcp.databricks.com"
      region       = workspace.region
    }
  } : null
}

output "regional_dns_mappings" {
  description = "DNS mappings for each region"
  value = {
    psc_regions = var.workspace_type == "psc" ? {
      for region, config in var.databricks_regions : region => {
        frontend_dns = "${region}.psc.gcp.databricks.com"
        frontend_ip  = config.frontend_pe_ip
        auth_dns     = "${region}.psc-auth.gcp.databricks.com"
        auth_ip      = config.frontend_pe_ip
        tunnel_dns   = "tunnel.${region}.gcp.databricks.com"
        tunnel_ip    = config.backend_pe_ip
      }
    } : null

    non_psc_regions = var.workspace_type == "non-psc" ? {
      for region, config in var.databricks_regions : region => {
        forwarding_zone = "${region}.gcp.databricks.com"
        forward_to      = ["8.8.8.8", "8.8.4.4"]
      }
    } : null
  }
}

output "nameservers" {
  description = "Nameservers for each DNS zone (for verification)"
  value = {
    psc_main        = var.workspace_type == "psc" ? try(google_dns_managed_zone.databricks_main[0].name_servers, null) : null
    psc_webapp      = var.workspace_type == "psc" ? try(google_dns_managed_zone.databricks_psc_webapp[0].name_servers, null) : null
    psc_auth        = var.workspace_type == "psc" ? try(google_dns_managed_zone.databricks_psc_auth[0].name_servers, null) : null
    psc_backend     = var.workspace_type == "psc" ? { for region, zone in google_dns_managed_zone.databricks_psc_backend : region => zone.name_servers } : null
    non_psc_regions = var.workspace_type == "non-psc" ? { for region, zone in google_dns_managed_zone.databricks_public_regional : region => zone.name_servers } : null
    accounts        = google_dns_managed_zone.databricks_accounts.name_servers
  }
}

output "verification_commands" {
  description = "Commands to verify DNS setup"
  value = <<-EOT
    # List all DNS zones
    gcloud dns managed-zones list --project=${var.vpc_project_id}

    # Test DNS resolution from VM in VPC (using GCP metadata DNS)
    ${var.workspace_type == "psc" ? join("\n    ", [
  "# PSC Workspace DNS verification:",
  "dig @169.254.169.254 ${try(element([for ws in var.workspaces : "${ws.workspace_id}.gcp.databricks.com"], 0), "YOUR-WORKSPACE-ID.gcp.databricks.com")}",
  "dig @169.254.169.254 ${try(element([for region in keys(var.databricks_regions) : "${region}.psc.gcp.databricks.com"], 0), "REGION.psc.gcp.databricks.com")}",
  "dig @169.254.169.254 ${try(element([for region in keys(var.databricks_regions) : "tunnel.${region}.gcp.databricks.com"], 0), "tunnel.REGION.gcp.databricks.com")}"
  ]) : ""}
    ${var.workspace_type == "non-psc" ? join("\n    ", [
  "# Non-PSC Workspace DNS verification:",
  "dig @169.254.169.254 YOUR-WORKSPACE-ID.${try(element(keys(var.databricks_regions), 0), "REGION")}.gcp.databricks.com"
]) : ""}

    # Test accounts console DNS
    dig @169.254.169.254 accounts.gcp.databricks.com
  EOT
}
