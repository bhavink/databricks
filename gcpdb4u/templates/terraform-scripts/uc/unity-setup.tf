variable "databricks_account_id" {}
variable "uc_admin_group_name" {}
variable databricks_admin_user {}

data "google_client_openid_userinfo" "me" {}
data "google_client_config" "current" {}


***REMOVED*** Random suffix for databricks resources
resource "random_string" "databricks_suffix" {
  special = false
  upper   = false
  length  = 3
}

// optional prefix for metastore name
locals {
  prefix = "unity"
}


***REMOVED*** extract workspace ID for unity catalog metastore assignment
***REMOVED*** or provide a hard coded value
locals {
  workspace_id = "<workspace-id>" //databricks_mws_workspaces.databricks_workspace.workspace_id
}

// create uc admin group
resource "databricks_group" "uc_admins" {
  provider     = databricks.accounts
  display_name = var.uc_admin_group_name
}

// create admin user1
resource "databricks_user" "admin_member0" { 
  provider     = databricks.accounts
  user_name = "${random_string.databricks_suffix.result}@databricks.com"
}

// retrieve existing user from account console
data "databricks_user" "admin_member1" {
  provider     = databricks.accounts
  user_name = var.databricks_admin_user
}

// retrieve existing user from account console
data "databricks_user" "admin_member2" {
  provider     = databricks.accounts
  user_name = var.google_service_account_email
}

// add user to group
resource "databricks_group_member" "admin_member0" { 
  provider     = databricks.accounts
  group_id  = databricks_group.uc_admins.id
  member_id = databricks_user.admin_member0.id
}

// add user to group
resource "databricks_group_member" "admin_member1" { 
  provider     = databricks.accounts
  group_id  = databricks_group.uc_admins.id
  member_id = data.databricks_user.admin_member1.id
}

// add user to group
resource "databricks_group_member" "admin_member2" { 
  provider     = databricks.accounts
  group_id  = databricks_group.uc_admins.id
  member_id = data.databricks_user.admin_member2.id
}

// create storage account for metastore

resource "google_storage_bucket" "unity_metastore" {
  name          = "${local.prefix}-metastore-${var.google_region}-${random_string.databricks_suffix.result}"
  location      = var.google_region
  force_destroy = true
}

// create metastore
resource "databricks_metastore" "this" {
  provider      = databricks.accounts
  name          = "primary-metastore-${var.google_region}-${random_string.databricks_suffix.result}"
  storage_root  = "gs://${google_storage_bucket.unity_metastore.name}"
  force_destroy = true
  owner         = var.uc_admin_group_name
  region = var.google_region
}

***REMOVED*** at this moment destroying databricks_metastore_data_access resource is not supported using TF
***REMOVED*** please use `terraform state rm databricks_metastore_data_access.first` and the manually delete 
***REMOVED*** metastore on the account console

resource "databricks_metastore_data_access" "first" {
  provider     = databricks.accounts
  metastore_id = databricks_metastore.this.id
  databricks_gcp_service_account {}
  name       = "the-keys" // any name
  is_default = true
}

resource "google_storage_bucket_iam_member" "unity_sa_admin" {
  depends_on = [
    databricks_metastore_data_access.first
  ]
  bucket = google_storage_bucket.unity_metastore.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${databricks_metastore_data_access.first.databricks_gcp_service_account[0].email}"
}

resource "google_storage_bucket_iam_member" "unity_sa_reader" {
  depends_on = [
    databricks_metastore_data_access.first
  ]
  bucket = google_storage_bucket.unity_metastore.name
  role   = "roles/storage.legacyBucketReader"
  member = "serviceAccount:${databricks_metastore_data_access.first.databricks_gcp_service_account[0].email}"
}

resource "databricks_metastore_assignment" "this" {
  provider             = databricks.accounts
  workspace_id         = local.workspace_id
  metastore_id         = databricks_metastore.this.id
  default_catalog_name = "main"
}


