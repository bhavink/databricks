variable "databricks_account_id" {}
variable "databricks_account_console_url" {}
variable "databricks_workspace_name" {}
variable "databricks_admin_user" {}
variable "google_shared_vpc_project" {}
variable "google_vpc_id" {}
variable "gke_node_subnet" {}
variable "gke_pod_subnet" {}
variable "gke_service_subnet" {}
variable "gke_master_ip_range" {}
variable "cmek_resource_id" {}
variable "google_pe_subnet" {}
variable "api_pe" {}
variable "relay_pe" {}


data "google_client_openid_userinfo" "me" {}
data "google_client_config" "current" {}


resource "google_service_account" "databricks" {
    account_id   = "databricks" #need to use "databricks"
    display_name = "Databricks SA for GKE nodes"
    project = var.google_project_name
}
output "service_account" {
    value       = google_service_account.databricks.email
    description = "Default SA for GKE nodes"
}

# # assign role to the gke default SA
resource "google_project_iam_binding" "databricks_gke_node_role" {
  project = "${var.google_project_name}"
  role = "roles/container.nodeServiceAccount"
  members = [
    "serviceAccount:${google_service_account.databricks.email}"
  ]
}

resource "databricks_mws_customer_managed_keys" "this" {
        provider = databricks.accounts
				account_id   = var.databricks_account_id
				gcp_key_info {
					kms_key_id   = var.cmek_resource_id
				}
				use_cases = ["STORAGE"]
			}

# Random suffix for databricks network and workspace
resource "random_string" "databricks_suffix" {
  special = false
  upper   = false
  length  = 2
}

# Provision databricks network configuration > backend vpc endpoint
resource "databricks_mws_vpc_endpoint" "relay_vpce" {
  provider = databricks.accounts
  account_id          = var.databricks_account_id
  vpc_endpoint_name   = "backend-relay-ep-${random_string.databricks_suffix.result}"
  gcp_vpc_endpoint_info {
    project_id        = var.google_shared_vpc_project
    psc_endpoint_name = var.relay_pe
    endpoint_region   = var.google_region
}
}

# Provision databricks network configuration > frontend vpc endpoint
resource "databricks_mws_vpc_endpoint" "backend_rest_vpce" {
  provider = databricks.accounts
  account_id          = var.databricks_account_id
  vpc_endpoint_name   = "frontend-api-ep-${random_string.databricks_suffix.result}"
  gcp_vpc_endpoint_info {
    project_id        = var.google_shared_vpc_project
    psc_endpoint_name = var.api_pe
    endpoint_region   = var.google_region
}
}

# Provision databricks private access configuration > applies to vpc endpoint
resource "databricks_mws_private_access_settings" "pas" {
  provider = databricks.accounts
  account_id                   = var.databricks_account_id
  private_access_settings_name = "pas-${random_string.databricks_suffix.result}"
  region                       = var.google_region
  public_access_enabled        = true        //cannot be changed after workspace is created
  private_access_level         = "ACCOUNT"
}

# Provision databricks network configuration
resource "databricks_mws_networks" "databricks_network" {
  provider     = databricks.accounts
  account_id   = var.databricks_account_id
  # name needs to be of length 3-30 incuding [a-z,A-Z,-_]
  network_name = "${var.google_shared_vpc_project}-nw-${random_string.databricks_suffix.result}"
  gcp_network_info {
    network_project_id    = var.google_shared_vpc_project
    vpc_id                = var.google_vpc_id
    subnet_id             = var.gke_node_subnet
    pod_ip_range_name     = var.gke_pod_subnet
    service_ip_range_name = var.gke_service_subnet
    subnet_region         = var.google_region
  }
  vpc_endpoints {
    dataplane_relay = [databricks_mws_vpc_endpoint.relay_vpce.vpc_endpoint_id]
    rest_api        = [databricks_mws_vpc_endpoint.backend_rest_vpce.vpc_endpoint_id]
  }
}
# Provision databricks workspace in a customer managed vpc
# https://docs.gcp.databricks.com/administration-guide/account-settings-gcp/workspaces.html#create-a-workspace-using-the-account-console

resource "databricks_mws_workspaces" "databricks_workspace" {
  provider       = databricks.accounts
  account_id     = var.databricks_account_id
  workspace_name = var.databricks_workspace_name
  location       = var.google_region
  cloud_resource_container {
    gcp {
      project_id = var.google_project_name
    }
  }
  private_access_settings_id = databricks_mws_private_access_settings.pas.private_access_settings_id
  network_id = databricks_mws_networks.databricks_network.network_id
  gke_config {
    connectivity_type = "PRIVATE_NODE_PUBLIC_MASTER"
    master_ip_range   = var.gke_master_ip_range
  }
  storage_customer_managed_key_id = databricks_mws_customer_managed_keys.this.customer_managed_key_id
}


data "databricks_group" "admins" {
  depends_on   = [ databricks_mws_workspaces.databricks_workspace ]
  provider     = databricks.workspace
  display_name = "admins"
}

resource "databricks_user" "me" {
  depends_on = [ databricks_mws_workspaces.databricks_workspace ]
  provider   = databricks.workspace
  user_name  = data.google_client_openid_userinfo.me.email
}

resource "databricks_group_member" "allow_me_to_login" {
  depends_on = [ databricks_mws_workspaces.databricks_workspace ]
  provider   = databricks.workspace
  group_id   = data.databricks_group.admins.id
  member_id  = databricks_user.me.id
}

resource "databricks_workspace_conf" "this" {
  depends_on = [ databricks_mws_workspaces.databricks_workspace ]
  provider   = databricks.workspace
  custom_config = {
    "enableIpAccessLists" = true
  }
}

resource "databricks_ip_access_list" "this" {
  depends_on = [ databricks_workspace_conf.this ]
  provider   = databricks.workspace
  label = "allow corp vpn1"
  list_type = "ALLOW"
  ip_addresses = [
    "44.228.166.17/32",
    "18.158.110.150/32",
    "18.193.11.166/32",
    "44.230.222.179/32"
    ]

}

output "workspace_url" {
  value = databricks_mws_workspaces.databricks_workspace.workspace_url
}

output "ingress_firewall_enabled" {
  value = databricks_workspace_conf.this.custom_config["enableIpAccessLists"]
}

output "ingress_firewall_ip_allowed" {
  value = databricks_ip_access_list.this.ip_addresses
}
