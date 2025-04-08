variable "databricks_account_id" {}
variable "databricks_account_console_url" {}
variable "databricks_workspace_name" {}
variable "databricks_admin_user" {}
variable "google_vpc_id" {}
variable "node_subnet" {}



data "google_client_openid_userinfo" "me" {}
data "google_client_config" "current" {}


resource "google_service_account" "databricks" {
    account_id   = "databricks" ***REMOVED***need to use "databricks"
    display_name = "Databricks SA for GCE nodes"
    project = var.google_project_name
}
output "service_account" {
    value       = google_service_account.databricks.email
    description = "Default SA for GCE nodes"
}

***REMOVED*** ***REMOVED*** assign role to the GCE default SA
resource "google_project_iam_binding" "databricks_GCE_node_role" {
  project = "${var.google_project_name}"
  role = "roles/container.nodeServiceAccount"
  members = [
    "serviceAccount:${google_service_account.databricks.email}"
  ]
}

***REMOVED*** Random suffix for databricks network and workspace
resource "random_string" "databricks_suffix" {
  special = false
  upper   = false
  length  = 2
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
    subnet_id             = var.node_subnet
    subnet_region         = var.google_region
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
  network_id = databricks_mws_networks.databricks_network.network_id
}


data "databricks_group" "admins" {
  depends_on   = [ databricks_mws_workspaces.databricks_workspace ]
  provider     = databricks.workspace
  display_name = "admins"
}

resource "databricks_user" "me" {
  depends_on = [ databricks_mws_workspaces.databricks_workspace ]
  provider   = databricks.workspace
  user_name  = var.databricks_admin_user
}


output "workspace_url" {
  value = databricks_mws_workspaces.databricks_workspace.workspace_url
}
