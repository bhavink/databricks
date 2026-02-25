//variable "databricks_account_id" {}
variable "databricks_account_console_url" {}
variable "databricks_workspace_name" {}
//variable "databricks_admin_user" {}
variable "google_shared_vpc_project" {}
variable "google_vpc_id" {}
variable "node_subnet" {}
variable "databricks_admin_user" {}

//data "google_client_openid_userinfo" "me" {}
//data "google_client_config" "current" {}

# Random suffix for databricks resources
resource "random_string" "databricks_suffix" {
  special = false
  upper   = false
  length  = 3
}


# Provision databricks network configuration
resource "databricks_mws_networks" "databricks_network" {
  provider   = databricks.accounts
  account_id = var.databricks_account_id
  # name needs to be of length 3-30 incuding [a-z,A-Z,-_]
  network_name = "${var.google_shared_vpc_project}-nw-${random_string.databricks_suffix.result}"
  gcp_network_info {
    network_project_id = var.google_shared_vpc_project
    vpc_id             = var.google_vpc_id
    subnet_id          = var.node_subnet
    subnet_region      = var.google_region
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
  network_id = databricks_mws_networks.databricks_network.network_id

}


// add a default user as a workspace admin
data "databricks_group" "admins" {
  depends_on   = [databricks_mws_workspaces.databricks_workspace]
  provider     = databricks.workspace
  display_name = "admins"
}

resource "databricks_user" "me" {
  depends_on = [databricks_mws_workspaces.databricks_workspace]
  provider   = databricks.workspace
  user_name  = var.databricks_admin_user
}

resource "databricks_group_member" "ws_admin_member0" {
  provider  = databricks.workspace
  group_id  = data.databricks_group.admins.id
  member_id = databricks_user.me.id
}


resource "databricks_workspace_conf" "this" {
  depends_on = [databricks_mws_workspaces.databricks_workspace]
  provider   = databricks.workspace
  custom_config = {
    "enableIpAccessLists" = true
  }
}

resource "databricks_ip_access_list" "this" {
  depends_on = [databricks_workspace_conf.this]
  provider   = databricks.workspace
  label      = "allow corp vpn1"
  # example allow list
  list_type = "ALLOW"
  ip_addresses = [
    "0.0.0.0/0",
    "18.158.110.150/32"
  ]

}

output "ingress_firewall_enabled" {
  value = databricks_workspace_conf.this.custom_config["enableIpAccessLists"]
}

output "ingress_firewall_ip_allowed" {
  value = databricks_ip_access_list.this.ip_addresses
}


output "workspace_url" {
  value = databricks_mws_workspaces.databricks_workspace.workspace_url
}

// extract workspace ID for unity catalog metastore assignment
locals {
  workspace_id = databricks_mws_workspaces.databricks_workspace.workspace_id
}


