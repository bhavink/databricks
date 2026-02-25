/*

https://registry.terraform.io/providers/databricks/databricks/latest/docs

Script to:

https://registry.terraform.io/providers/databricks/databricks/latest/docs/guides/unity-catalog-gcp

- Create GCS storage account aka default storage account
- Create Unity metastore
- Assign Unity service account to default storage account


https://registry.terraform.io/providers/databricks/databricks/latest/docs/resources/mws_permission_assignment

- Create group for metastore
- Add user and service account to group
- Assign group to metastore with admin privileges
- Assign workspace to metastore
- Create unity admin groups
- Add user's to unity admin groups
*/


//variable "databricks_account_id" {}
variable "uc_admin_group_name" {}
variable "group_name1" {}
variable "group_name2" {}
variable "metastore_name" {}

data "google_client_openid_userinfo" "me" {}
data "google_client_config" "current" {}


// create unity catalog admin group
resource "databricks_group" "uc_admins" {
  provider     = databricks.accounts
  display_name = var.uc_admin_group_name
}

// create uc admin user
resource "databricks_user" "admin_member1" {
  provider  = databricks.accounts
  user_name = "${random_string.databricks_suffix.result}@example.com"
}

// retrieve existing user/service account from account console
data "databricks_user" "admin_member2" {
  provider  = databricks.accounts
  user_name = var.google_service_account_email
}

// add user to uc admin group
resource "databricks_group_member" "admin_member1" {
  provider  = databricks.accounts
  group_id  = databricks_group.uc_admins.id
  member_id = databricks_user.admin_member1.id
}

// add user to uc admin group
resource "databricks_group_member" "admin_member2" {
  provider  = databricks.accounts
  group_id  = databricks_group.uc_admins.id
  member_id = data.databricks_user.admin_member2.id // SA already exists in the account console
}

// create managed storage account for metastore
// https://docs.gcp.databricks.com/data-governance/unity-catalog/index.html#managed-storage
resource "google_storage_bucket" "unity_metastore" {
  name          = "${var.metastore_name}-${var.google_region}-${random_string.databricks_suffix.result}"
  location      = var.google_region
  force_destroy = true
}

# // create metastore
# // https://docs.gcp.databricks.com/data-governance/unity-catalog/create-metastore.html

resource "databricks_metastore" "this" {
  depends_on = [
    databricks_mws_workspaces.databricks_workspace
  ]
  provider      = databricks.accounts
  name          = "${var.metastore_name}-${var.google_region}-${random_string.databricks_suffix.result}"
  storage_root  = "gs://${google_storage_bucket.unity_metastore.name}"
  force_destroy = true
  owner         = var.uc_admin_group_name
  region        = var.google_region
}

# at this moment destroying databricks_metastore_data_access resource is not supported using TF
# please use `terraform state rm databricks_metastore_data_access.first` and re-run terraform destroy

//https://docs.gcp.databricks.com/data-governance/unity-catalog/create-metastore.html#step-2-create-the-metastore-and-generate-a-service-account
resource "databricks_metastore_data_access" "first" {
  depends_on = [
    databricks_metastore.this
  ]
  provider     = databricks.accounts
  metastore_id = databricks_metastore.this.id
  databricks_gcp_service_account {}
  name       = "default-storage-creds" // storage credentials created for the default storage account
  is_default = true
}

//https://docs.gcp.databricks.com/data-governance/unity-catalog/create-metastore.html#step-3-give-the-service-account-access-to-your-gcs-bucket-and-assign-workspaces
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
  depends_on           = [databricks_mws_workspaces.databricks_workspace]
  provider             = databricks.accounts
  workspace_id         = local.workspace_id
  metastore_id         = databricks_metastore.this.id
  default_catalog_name = "main"
}

resource "databricks_grants" "all_grants" {
  provider  = databricks.workspace
  metastore = databricks_metastore.this.id
  grant {
    principal  = var.google_service_account_email
    privileges = ["CREATE_CATALOG", "CREATE_EXTERNAL_LOCATION", "CREATE_STORAGE_CREDENTIAL"]
  }
  grant {
    principal  = var.databricks_admin_user
    privileges = ["USE_CONNECTION", "CREATE_EXTERNAL_LOCATION", "CREATE_STORAGE_CREDENTIAL"]
  }
  depends_on = [
    databricks_metastore_assignment.this
  ]
}

/* At this stage we have Unity Catalog created
* create a UC admins groups and added members to it
* assigned a workspace to UC
* created a catalog called "main"
* next iam-assignments.tf where we'll take care of assigning groups with specific roles to use UC
*/

