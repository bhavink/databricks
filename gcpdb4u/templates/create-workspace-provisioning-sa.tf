/**
You have a choice to either create a custom role with required permissions to create databricks workspace or
use builtin roles. We'll leave it upto the end user preference on what to use.

Please make sure to carefully go thru the script before running it.

If you are using custom role then you do not need to use builtin-roles block
Please comment it out.

Databricks accounts console is available at: https://accounts.gcp.databricks.com
SA created needs to be added to the accounts console as a "User" (https://docs.gcp.databricks.com/administration-guide/account-settings-gcp/admin-users.html) 
and need to have admin role assigned (https://docs.gcp.databricks.com/administration-guide/users-groups/users.html***REMOVED***account-admin)

*/


***REMOVED*** used with sa and workspace name
variable "prefix" { default = "test" }

variable "databricks_account_id" { default = "e11e38c5-a449-47b9-b37f-0fa36c821612" }

***REMOVED*** if you are not using shared vpc then the host and service project would have the same project id
variable "google_host_project_id" { default = "labs-byovpc-test" }

***REMOVED*** this is where databricks managed GKE will be created
variable "google_service_project_id" { default = "labs-byovpc-test" }

variable "google_region" { default = "us-central1" }




terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
    }
  }
}

provider "google" {
    project = var.google_service_project_id
    region  = var.google_region
}

resource "google_service_account" "sa2" {
    account_id   = "${var.prefix}-ws-sa"
    display_name = "Service Account for Databricks Provisioning"
}
output "service_account" {
    value       = google_service_account.sa2.email
    description = "Add this email as a user in the Databricks account console"
}
***REMOVED*** create this role if GKE and VPC resides in same GCP project
resource "google_project_iam_custom_role" "workspace_creator" {
    role_id = "${var.prefix}_workspace_creator"
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
    "serviceusage.services.enable",
    "compute.networks.get",
    "compute.projects.get",
    "compute.subnetworks.get"
    ]
}
***REMOVED*** assign custom role to the workspace create SA
resource "google_project_iam_member" "sa2_can_create_workspaces" {
    role   = google_project_iam_custom_role.workspace_creator.id
    project = "${var.google_service_project_id}"
    member = "serviceAccount:${google_service_account.sa2.email}"
}

***REMOVED*** you could also add builtin roles to the SA instead of using custom role
resource "google_project_iam_member" "service_project_role" {
  for_each = toset([
    "roles/editor",
    "roles/resourcemanager.projectIamAdmin"
  ])
  role = each.key
  member = "serviceAccount:${google_service_account.sa2.email}"
  project = "${var.google_service_project_id}"
}

***REMOVED*** applicable only if you are using a shared vpc where VPC resides in host project and GKE in service project 
resource "google_project_iam_binding" "host_project_role" {
  project = "${var.google_host_project_id}"
  role = "roles/viewer"
  members = [
    "serviceAccount:${google_service_account.sa2.email}"
  ]
}

data "google_client_config" "current" {
}

output "custom_role_url" {
    value = "https://console.cloud.google.com/iam-admin/roles/details/projects%3C${data.google_client_config.current.project}%3Croles%3C${google_project_iam_custom_role.workspace_creator.role_id}"
}

output "psa"{
  value = "SA created: ${google_service_account.sa2.email}\nPlease make sure to add this SA to databricks accounts console and assign it accounts admin role"
}