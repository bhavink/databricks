/*

There are 2 GCP Service Accounts involved. Let's call them SA-1 and SA-2.
SA-1 = has ServiceAccountTokenCreator role on the GCP project where databricks workspace is created. 
SA-1 impersonates databricks workspace creator SA aka SA-2.
SA-2 has set of permissions to create the workspace. 
SA-2 is added to databricks account console with account admin role i.e.
visit https://accounts.gcp.databricks.com > User Management > Search for the SA email and verify its role
SA-1 impersonates SA-2

*/

/* 
Before youu begin please run the following command and make sure the right account is configured to use gcloud command.
account used by `gcloud auth list`
*/

# gcloud auth activate-service-account token-creator@labs-byovpc-test.iam.gserviceaccount.com -key-file=token-creator-sa-creds.json

variable "databricks_delegate" {
 description = "This is SA-1. Allow either user:user.name@example.com, group:deployers@example.com or serviceAccount:sa1@project.iam.gserviceaccount.com to impersonate created service account aka SA-2"
 type        = list(string)
 # example of using a user identity with owner role on the project or a service account with tokenCreator role.
 default = ["user:bhavin.kukadia@databricks.com","serviceAccount:token-creator@labs-byovpc-test.iam.gserviceaccount.com"]
 

}

/*
in case if you are NOT using a shared vpc than service and host project id will be same
host project hosts the vpc used by databricks
*/

# TODO: All these variables has be set to the proper values
variable "project" {
  default = "labs-byovpc-test"
}
variable "host_project" {
  default = "labs-byovpc-test"
}
variable "databricks_account_id" {
  default = "e11e38c5-a449-47b9-b37f-0fa36c821612"
}
variable "databricks_workspace_provisioner_sa_alias" {
  default = "databricks-workspace-creator"
}
variable "databricks_region" {
  default = "us-central1"
}
variable "databricks_vpc_id" {
  default = "tf-test-vpc"
}
variable "databricks_node_subnet" {
  default = "tf-node-subnet"
}
variable "databricks_pod_subnet" {
  default = "tf-pod-subnet"
}
variable "databricks_service_subnet" {
  default = "tf-service-subnet"
}
variable "databricks_gke_master_ip_range" {
  default = "10.39.0.0/28"
}


terraform {
  required_providers {
    databricks = {
      source = "databricks/databricks"
      # version = "1.8.0"
    }
    google = {
      source  = "hashicorp/google"
    }
  }
}

data "google_client_openid_userinfo" "me" {
}

# Service account for databricks workspace creation aka SA-2

resource "google_service_account" "sa_databricks_workspace_creator" {
  project      = var.project
  account_id   = "databricks-workspace-creator"
  display_name = "Service Account For Databricks Workspace Creation"
}

output "databricks_service_account" {
  value       = google_service_account.sa_databricks_workspace_creator.email
  description = "Add this email as a user in the Databricks account console"
}

data "google_iam_policy" "databricks_sa_token_creator" {
  binding {
    role    = "roles/iam.serviceAccountTokenCreator"
    members = var.databricks_delegate
  }
}

resource "google_service_account_iam_policy" "databricks_sa_impersonator" {
  service_account_id = google_service_account.sa_databricks_workspace_creator.name
  policy_data        = data.google_iam_policy.databricks_sa_token_creator.policy_data
  depends_on         = [google_service_account.sa_databricks_workspace_creator]
}

resource "google_project_iam_custom_role" "databricks_workspace_creator" {
  project = var.project
  role_id = "databricksWorkspaceCreator"
  title   = "Databricks Workspace Creator"
  permissions = [
    "iam.serviceAccounts.getIamPolicy",
    "iam.serviceAccounts.setIamPolicy",
    "iam.roles.create",
    "iam.roles.delete",
    "iam.roles.get",
    "iam.roles.update",
    "resourcemanager.projects.get",
    "resourcemanager.projects.getIamPolicy",
    "resourcemanager.projects.setIamPolicy",
    "serviceusage.services.get",
    "serviceusage.services.list",
    "serviceusage.services.enable"
  ]
}

data "google_client_config" "current" {}

output "custom_role_url" {
  value = "https://console.cloud.google.com/iam-admin/roles/details/projects%3C${data.google_client_config.current.project}%3Croles%3C${google_project_iam_custom_role.databricks_workspace_creator.role_id}"
}

resource "google_project_iam_member" "iam_member_databricks_workspace_creator" {
  project = var.project
  role    = google_project_iam_custom_role.databricks_workspace_creator.id
  member  = "serviceAccount:${google_service_account.sa_databricks_workspace_creator.email}"
  depends_on = [
    google_project_iam_custom_role.databricks_workspace_creator,
    google_service_account.sa_databricks_workspace_creator
  ]
}

# Applicable only if you are using a shared vpc where VPC resides in host project and GKE in service project 
resource "google_project_iam_member" "host_project_role" {
  project 	= var.host_project
  role 		= "roles/compute.networkUser"
  member 	= "serviceAccount:${google_service_account.sa_databricks_workspace_creator.email}"
}


resource "google_service_account" "databricks" {
    account_id   = "databricks" #need to use "databricks"
    display_name = "Databricks SA for GKE nodes"
    project = var.project
}
output "service_account" {
    value       = google_service_account.databricks.email
    description = "Default SA for GKE nodes"
}

# minimum persmissions requied to propagate tags set at databricks cluster level to underlying GCP resources.
# this role will be assigned to an SA which is then used by GKE as a nodeServiceAccount instead of using the default compute engine

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

# assign custom role to the gke default SA
resource "google_project_iam_member" "databricks_gke_custom_role" {
    role   = google_project_iam_custom_role.databricks_gke_custom_role.id
    project = "${var.project}"
    member = "serviceAccount:${google_service_account.databricks.email}"
}

# assign role to the gke default SA
resource "google_project_iam_binding" "databricks_gke_node_role" {
  project = "${var.project}"
  role = "roles/container.nodeServiceAccount"
  members = [
    "serviceAccount:${google_service_account.databricks.email}"
  ]
}



# Initialize provider in "accounts" mode to provision new workspace
provider "databricks" {
  alias                  = "accounts"
  host                   = "https://accounts.gcp.databricks.com"
  google_service_account = "${var.databricks_workspace_provisioner_sa_alias}@${var.project}.iam.gserviceaccount.com"
  account_id             = var.databricks_account_id
}



# Random suffix for databricks network and workspace
resource "random_string" "databricks_suffix" {
  special = false
  upper   = false
  length  = 2
}

# Provision databricks network configuration
resource "databricks_mws_networks" "databricks_network" {
  provider     = databricks.accounts
  account_id   = var.databricks_account_id
  # name needs to be of length 3-30 incuding [a-z,A-Z,-_]
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

# Provision databricks workspace in a customer managed vpc
# https://docs.gcp.databricks.com/administration-guide/account-settings-gcp/workspaces.html#create-a-workspace-using-the-account-console

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

# Provision databricks workspace in a databricks managed vpc
# https://docs.gcp.databricks.com/administration-guide/account-settings-gcp/workspaces.html#create-a-workspace-using-the-account-console

# resource "databricks_mws_workspaces" "this" {
#  provider       = databricks.accounts
#  account_id     = var.databricks_account_id
#  workspace_name = "bk-tf-demo1"
#  location       = data.google_client_config.current.region


#  cloud_resource_container {
#     gcp {
#       project_id = var.google_project
#     }
#   }
# }


# Output host url
output "databricks_host" {
  value = databricks_mws_workspaces.databricks_workspace.workspace_url
}

### Databricks Workspace Automation (End) ###


### Add admin user to the workspace

provider "databricks" {
 alias                  = "workspace"
 host                   = databricks_mws_workspaces.databricks_workspace.workspace_url
 google_service_account = google_service_account.sa_databricks_workspace_creator.email
}


data "databricks_group" "admins" {
 depends_on   = [databricks_mws_workspaces.databricks_workspace]
 provider     = databricks.workspace
 display_name = "admins"
}

# Adds user to the workspace
resource "databricks_user" "me" {
 depends_on = [databricks_mws_workspaces.databricks_workspace]
 provider  = databricks.workspace
 #user_name = data.google_client_openid_userinfo.me.data
 user_name = "bhavin.kukadia@databricks.com"
}

# Assigns workspace admin role to the user added
resource "databricks_group_member" "allow_me_to_login" {
 depends_on = [databricks_mws_workspaces.databricks_workspace]
 
 provider  = databricks.workspace
 group_id  = data.databricks_group.admins.id
 member_id = databricks_user.me.id
}