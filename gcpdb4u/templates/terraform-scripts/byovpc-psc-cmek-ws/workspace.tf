variable "databricks_account_id" {}
variable "databricks_account_console_url" {}
variable "databricks_workspace_name" {}
variable "databricks_admin_user" {}
variable "google_vpc_id" {}
variable "gke_node_subnet" {}
variable "gke_pod_subnet" {}
variable "gke_service_subnet" {}
variable "gke_master_ip_range" {}
variable "cmek_resource_id" {}
variable "google_pe_subnet" {}
variable "workspace_pe" {}
variable "relay_pe" {}
variable "relay_pe_ip_name" {}
variable "workspace_pe_ip_name" {}
variable "relay_service_attachment" {}
variable "workspace_service_attachment" {}

data "google_client_openid_userinfo" "me" {}
data "google_client_config" "current" {}

/*
Service account attached to the GKE cluster to spin up GKE nodes
GKE node pool use this service account to call Google Cloud APIs
instead of using the default compute engine SA, databricks will use this SA
this is different than the workload identity aka SA that you'll use to connect to your data sources as explained here
https://docs.gcp.databricks.com/archive/compute/configure.html***REMOVED***google-service-account
*/


resource "google_service_account" "databricks" {
    account_id   = "databricks" ***REMOVED***need to use "databricks"
    display_name = "Databricks SA for GKE nodes"
    project = var.google_project_name
}

***REMOVED*** ***REMOVED*** assign role to the gke default SA
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
				use_cases = ["STORAGE","MANAGED"]

        lifecycle {
          ignore_changes = all
        }
			}

***REMOVED*** Random suffix for databricks network and workspace
resource "random_string" "databricks_suffix" {
  special = false
  upper   = false
  length  = 2
}

***REMOVED*** Provision databricks network configuration > backend vpc endpoint
resource "databricks_mws_vpc_endpoint" "relay_vpce" {
  depends_on = [ google_compute_forwarding_rule.backend_psc_ep ]
  provider = databricks.accounts
  account_id          = var.databricks_account_id
  vpc_endpoint_name   = "backend-relay-ep-${random_string.databricks_suffix.result}"
  gcp_vpc_endpoint_info {
    project_id        = var.google_shared_vpc_project
    psc_endpoint_name = var.relay_pe
    endpoint_region   = var.google_region
}
}

***REMOVED*** Provision databricks network configuration > frontend vpc endpoint
resource "databricks_mws_vpc_endpoint" "workspace_vpce" {
  depends_on = [ google_compute_forwarding_rule.frontend_psc_ep ]
  provider = databricks.accounts
  account_id          = var.databricks_account_id
  vpc_endpoint_name   = "frontend-workspace-ep-${random_string.databricks_suffix.result}"
  gcp_vpc_endpoint_info {
    project_id        = var.google_shared_vpc_project
    psc_endpoint_name = var.workspace_pe
    endpoint_region   = var.google_region
}
}

***REMOVED*** Provision databricks private access configuration > applies to vpc endpoint
resource "databricks_mws_private_access_settings" "pas" {
  provider = databricks.accounts
  account_id                   = var.databricks_account_id
  private_access_settings_name = "pas-${random_string.databricks_suffix.result}"
  region                       = var.google_region
  
  /*
  
  Please carefully read thru this doc before proceeding
  https://docs.gcp.databricks.com/administration-guide/cloud-configurations/gcp/private-service-connect.html***REMOVED***step-6-create-a-databricks-private-access-settings-object

  Public access enabled: Specify if public access is allowed. 
  Choose this value carefully because it cannot be changed after the private access settings object is created.

  If public access is enabled, users can configure the IP access lists to allow/block public access (from the public internet) 
  to the workspaces that use this private access settings object.

  If public access is disabled, no public traffic can access the workspaces that use this private access settings object. 
  The IP access lists do not affect public access.

  */

  public_access_enabled        = false        ***REMOVED***false
  
  /*
  Private access level: A specification to restrict access to only authorized Private Service Connect connections. 
  It can be one of the below values:

  Account: Any VPC endpoints registered with your Databricks account can access this workspace. This is the default value.
  Endpoint: Only the VPC endpoints that you specify explicitly can access the workspace. 
  If you choose this value, you can choose from among your registered VPC endpoints.
  */
  private_access_level         = "ACCOUNT"
}

***REMOVED*** Provision databricks network configuration
  resource "databricks_mws_networks" "databricks_network" {
  provider     = databricks.accounts
  account_id   = var.databricks_account_id
  ***REMOVED*** name needs to be of length 3-30 incuding [a-z,A-Z,-_]
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
    rest_api        = [databricks_mws_vpc_endpoint.workspace_vpce.vpc_endpoint_id]
  }
}
***REMOVED*** Provision databricks workspace in a customer managed vpc
***REMOVED*** https://docs.gcp.databricks.com/administration-guide/account-settings-gcp/workspaces.html***REMOVED***create-a-workspace-using-the-account-console

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
  managed_services_customer_managed_key_id = databricks_mws_customer_managed_keys.this.customer_managed_key_id
}


data "databricks_group" "admins" {
  depends_on   = [ databricks_mws_workspaces.databricks_workspace ]
  provider     = databricks.workspace
  display_name = "admins"
}

resource "databricks_user" "me" {
  depends_on = [ databricks_mws_workspaces.databricks_workspace ]
  provider   = databricks.workspace
  user_name  = var.databricks_admin_user //data.google_client_openid_userinfo.me.email
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
    "69.174.135.244",
    "165.225.0.0/17",
    "185.46.212.0/22",
    "104.129.192.0/20",
    "165.225.192.0/18",
    "147.161.128.0/17",
    "136.226.0.0/16",
    "137.83.128.0/18",
    "167.103.0.0/16",
    "34.236.11.250/32",
    "44.228.166.17/32",
    "18.158.110.150/32",
    "18.193.11.166/32",
    "44.230.222.179/32"
    ]

}
output "service_account" {
    value       = "Default SA attached to GKE nodes ${google_service_account.databricks.email}"
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