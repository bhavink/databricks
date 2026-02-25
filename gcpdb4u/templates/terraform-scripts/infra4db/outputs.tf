output "vpc_id" {
  description = "The ID of the VPC"
  value       = google_compute_network.vpc.id
}

output "network_details" {
  description = "Details of the network including Subnets, PSC Subnets, NAT Gateways, and Routers"
  value = {
    subnets = {
      for k, v in google_compute_subnetwork.subnets : k => {
        name   = v.name
        region = v.region
        cidr   = v.ip_cidr_range
        id     = v.id
      }
    }
    psc_subnets = {
      for k, v in google_compute_subnetwork.psc_subnets : k => {
        name   = v.name
        region = v.region
        cidr   = v.ip_cidr_range
        id     = v.id
      }
    }
    nat_gateways = {
      for k, v in google_compute_router_nat.nats : k => {
        name    = v.name
        region  = google_compute_router.routers[k].region
        nat_ips = v.nat_ips
      }
    }
    routers = {
      for k, v in google_compute_router.routers : k => {
        name   = v.name
        region = v.region
        id     = v.id
      }
    }
  }
}


output "service_accounts" {
  description = "List of service accounts created"
  value = [
    google_service_account.databricks_compute.email, # Reference to the created service account
    // Add more service accounts as needed
  ]
}


# Outputs for KMS resources
output "databricks_keyring_ids" {
  value = { for keyring_name, ring in google_kms_key_ring.databricks_keyring : keyring_name => ring.id }
}

output "databricks_cmek_ids" {
  value = { for cmek_name, cmek in google_kms_crypto_key.databricks_cmek : cmek_name => cmek.id }
}


output "relay_psc_endpoints" {
  description = "List of created PSC endpoints with all details"
  value = {
    for k, v in google_compute_forwarding_rule.relay_psc_ep :
    k => {
      name                           = v.name
      id                             = v.id
      region                         = v.region
      network                        = v.network
      subnetwork                     = v.subnetwork
      ip_address                     = v.ip_address
      target                         = v.target
      service_directory_registration = try(v.service_directory_registration, null) # Optional
      labels                         = v.labels
    }
  }
}


output "relay_pe_ip_addresses" {
  value       = { for region, addr in google_compute_address.relay_pe_ip_address : region => addr.address }
  description = "Relay PSC IP addresses per region"
}

output "workspace_pe_ip_addresses" {
  value       = { for region, addr in google_compute_address.workspace_pe_ip_address : region => addr.address }
  description = "Workspace PSC IP addresses per region"
}


output "relay_psc_status" {
  value = { for region in keys(var.psc_attachments) : region => google_compute_forwarding_rule.relay_psc_ep[region].psc_connection_status }
}

output "workspace_psc_endpoints" {
  description = "List of created workspace PSC endpoints with all details"
  value = {
    for k, v in google_compute_forwarding_rule.workspace_psc_ep :
    k => {
      name                           = v.name
      id                             = v.id
      region                         = v.region
      network                        = v.network
      subnetwork                     = v.subnetwork
      ip_address                     = v.ip_address
      target                         = v.target
      service_directory_registration = try(v.service_directory_registration, null) # Optional
      labels                         = v.labels
    }
  }
}


output "workspace_psc_status" {
  value = { for region in keys(var.psc_attachments) : region => google_compute_forwarding_rule.workspace_psc_ep[region].psc_connection_status }
}

output "custom_roles" {
  description = "List of custom roles created"
  value = [
    google_project_iam_custom_role.databricks_creator_role.name,     # Reference to the custom role for workspace creation
    google_project_iam_custom_role.databricks_creator_role_vpc.name, # Reference to the custom role for VPC project

  ]
}