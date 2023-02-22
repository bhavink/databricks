/*

There are 2 GCP identities involved. Let's call them ID-1 and ID-2.
ID-1 = Is the user principal or service account running the terraform script. 
ID-2 = Service Account which has permissions and role to create a databricks workspace, typically the desired role is
project/IAMAdmin and project/Editor. In this example we are using terraform@labs-byovpc-test.iam.gserviceaccount.com as ID-2
ID-2 is added to databricks account console with account admin role i.e.
visit https://accounts.gcp.databricks.com > User Management > Search for the SA email and verify its role
ID-1 impersonates ID-2 using the "second" method mentioned over here[https://cloud.google.com/blog/topics/developers-practitioners/using-google-cloud-service-account-impersonation-your-terraform-code]
ID-1 doesn't need any kind of permission on the GCP project where Databricks workspace is created.

*/


terraform {
  required_providers {
    databricks = {
      source = "databricks/databricks"
      ***REMOVED*** version = "1.8.0"
    }
    google = {
      source  = "hashicorp/google"
    }
  }
}

locals {
 terraform_service_account = var.databricks_workspace_creator_sa
}

provider "google" {
 alias = "impersonation"
 scopes = [
   "https://www.googleapis.com/auth/cloud-platform",
   "https://www.googleapis.com/auth/userinfo.email"
 ]
}

data "google_service_account_access_token" "default" {
 provider               	= google.impersonation
 target_service_account 	= local.terraform_service_account
 scopes                 	= ["userinfo-email", "cloud-platform"]
 lifetime               	= "1200s"
}

data "google_client_openid_userinfo" "me" {
}

data "google_client_config" "current" {}


***REMOVED*** Applicable only if you are using a shared vpc where VPC resides in host project and GKE in service project 
resource "google_project_iam_member" "host_project_role" {
  project 	= var.host_project
  role 		= "roles/compute.networkUser"
  member 	= "serviceAccount:${local.terraform_service_account}"
}

resource "google_service_account" "databricks" {
    account_id   = "databricks" ***REMOVED***need to use "databricks"
    display_name = "Databricks SA for GKE nodes"
    project = var.project
}
output "service_account" {
    value       = google_service_account.databricks.email
    description = "Default SA for GKE nodes"
}

***REMOVED*** minimum persmissions requied to propagate tags set at databricks cluster level to underlying GCP resources.
***REMOVED*** this role will be assigned to an SA which is then used by GKE as a nodeServiceAccount instead of using the default compute engine

resource "google_project_iam_custom_role" "databricks_gke_custom_role" {
    role_id = "databricks_default_gke_compute"
    title   = "Databricks SA for VMs"
    project = var.project
    permissions = [
    "compute.disks.get",
    "compute.disks.setLabels",
    "compute.instances.get",
    "compute.instances.setLabels"
    ]
}

***REMOVED*** assign custom role to the gke default SA
resource "google_project_iam_member" "databricks_gke_custom_role" {
    role   = google_project_iam_custom_role.databricks_gke_custom_role.id
    project = "${var.project}"
    member = "serviceAccount:${google_service_account.databricks.email}"
}

***REMOVED*** assign role to the gke default SA
resource "google_project_iam_binding" "databricks_gke_node_role" {
  project = "${var.project}"
  role = "roles/container.nodeServiceAccount"
  members = [
    "serviceAccount:${google_service_account.databricks.email}"
  ]
}



***REMOVED*** Initialize provider in "accounts" mode to provision new workspace
provider "databricks" {
  alias                  = "accounts"
  host                   = "https://accounts.staging.gcp.databricks.com"
  google_service_account = local.terraform_service_account
  account_id             = var.databricks_account_id
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
  network_name = "${var.project}-nw-${random_string.databricks_suffix.result}"
  gcp_network_info {
    network_project_id    = var.project
    vpc_id                = var.databricks_vpc_id
    subnet_id             = var.databricks_node_subnet
    subnet_region         = var.databricks_region
    pod_ip_range_name     = var.databricks_pod_subnet
    service_ip_range_name = var.databricks_service_subnet
  }
}

***REMOVED*** Provision databricks workspace in a customer managed vpc
***REMOVED*** https://docs.gcp.databricks.com/administration-guide/account-settings-gcp/workspaces.html***REMOVED***create-a-workspace-using-the-account-console

resource "databricks_mws_workspaces" "databricks_workspace" {
  provider       = databricks.accounts
  account_id     = var.databricks_account_id
  workspace_name = "${var.project}-${random_string.databricks_suffix.result}"
  location       = var.databricks_region

  cloud_resource_container {
    gcp {
      project_id = var.project
    }
  }

  network_id = databricks_mws_networks.databricks_network.network_id

  gke_config {
    connectivity_type = "PRIVATE_NODE_PUBLIC_MASTER"
    master_ip_range   = var.databricks_gke_master_ip_range
  }
}

***REMOVED*** Provision databricks workspace in a databricks managed vpc
***REMOVED*** https://docs.gcp.databricks.com/administration-guide/account-settings-gcp/workspaces.html***REMOVED***create-a-workspace-using-the-account-console

***REMOVED*** resource "databricks_mws_workspaces" "this" {
***REMOVED***  provider       = databricks.accounts
***REMOVED***  account_id     = var.databricks_account_id
***REMOVED***  workspace_name = "bk-tf-demo1"
***REMOVED***  location       = data.google_client_config.current.region


***REMOVED***  cloud_resource_container {
***REMOVED***     gcp {
***REMOVED***       project_id = var.google_project
***REMOVED***     }
***REMOVED***   }
***REMOVED*** }


***REMOVED*** Output host url
output "databricks_host" {
  value = databricks_mws_workspaces.databricks_workspace.workspace_url
}

***REMOVED******REMOVED******REMOVED*** Databricks Workspace Automation (End) ***REMOVED******REMOVED******REMOVED***


***REMOVED******REMOVED******REMOVED*** Add admin user to the workspace

provider "databricks" {
 alias                  = "workspace"
 host                   = databricks_mws_workspaces.databricks_workspace.workspace_url
 google_service_account = local.terraform_service_account
}


data "databricks_group" "admins" {
 depends_on   = [databricks_mws_workspaces.databricks_workspace]
 provider     = databricks.workspace
 display_name = "admins"
}

***REMOVED*** Adds user to the workspace
resource "databricks_user" "me" {
 depends_on = [databricks_mws_workspaces.databricks_workspace]
 provider  = databricks.workspace
 ***REMOVED***user_name = data.google_client_openid_userinfo.me.data
 user_name = var.databricks_admin_user
}

***REMOVED*** Assigns workspace admin role to the user added
resource "databricks_group_member" "allow_me_to_login" {
 depends_on = [databricks_mws_workspaces.databricks_workspace]
 
 provider  = databricks.workspace
 group_id  = data.databricks_group.admins.id
 member_id = databricks_user.me.id
}