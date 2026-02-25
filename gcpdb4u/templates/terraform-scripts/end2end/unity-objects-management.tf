/*
Please carefully read thru this doc [ https://docs.gcp.databricks.com/data-governance/unity-catalog/manage-external-locations-and-credentials.html ]
We'll be automating the following steps using
https://registry.terraform.io/providers/databricks/databricks/latest/docs/guides/unity-catalog-gcp#create-unity-catalog-objects-in-the-metastore
*/


variable "external_storage" {}

/*
https://docs.gcp.databricks.com/data-governance/unity-catalog/create-catalogs.html
Create catalog
Grant permissions to a group on catalog
*/

resource "databricks_catalog" "dev" {
  provider     = databricks.workspace
  metastore_id = databricks_metastore.this.id
  name         = "dev"
  comment      = "dev catalog for dev workspace"
  properties = {
    purpose = "development"
  }
  // make sure a metastore isassigned to workspace
  depends_on = [databricks_metastore_assignment.this]
}

resource "databricks_grants" "dev" {
  provider = databricks.workspace
  catalog  = databricks_catalog.dev.name
  grant {
    principal  = var.group_name1 // group or an email id
    privileges = ["USE_CATALOG", "CREATE_SCHEMA"]
    /*
    https://docs.databricks.com/api/workspace/grants/update

    "READ_PRIVATE_FILES" "WRITE_PRIVATE_FILES" "CREATE" "USAGE" "USE_CATALOG" "USE_SCHEMA" 
    "CREATE_SCHEMA" "CREATE_VIEW" "CREATE_EXTERNAL_TABLE" "CREATE_MATERIALIZED_VIEW" 
    "CREATE_FUNCTION" "CREATE_MODEL" "CREATE_CATALOG" "CREATE_MANAGED_STORAGE" 
    "CREATE_EXTERNAL_LOCATION" "CREATE_STORAGE_CREDENTIAL" "CREATE_SHARE" 
    "CREATE_RECIPIENT" "CREATE_PROVIDER" "USE_SHARE" "USE_RECIPIENT" "USE_PROVIDER" 
    "USE_MARKETPLACE_ASSETS" "SET_SHARE_PERMISSION" "SELECT" "MODIFY" "REFRESH" 
    "EXECUTE" "READ_FILES" "WRITE_FILES" "CREATE_TABLE" "ALL_PRIVILEGES" 
    "CREATE_CONNECTION" "USE_CONNECTION" "APPLY_TAG" "CREATE_FOREIGN_CATALOG" 
    "MANAGE_ALLOWLIST" "CREATE_VOLUME" "CREATE_EXTERNAL_VOLUME" "READ_VOLUME" 
    "WRITE_VOLUME"
    */

  }
  grant {
    principal  = var.group_name2 // group or an email id
    privileges = ["USE_CATALOG", "CREATE_SCHEMA"]
  }
  grant {
    principal  = var.databricks_admin_user
    privileges = ["USE_CATALOG", "CREATE_SCHEMA", "USE_SCHEMA"]
  }
  depends_on = [databricks_mws_permission_assignment.add_admin_group, databricks_mws_permission_assignment.add_non_admin_group]
}

/*
https://docs.gcp.databricks.com/data-governance/unity-catalog/create-schemas.html
Create database / schema
Grant permissions to groups on catalog.database
*/

resource "databricks_schema" "dev_database" {
  provider     = databricks.workspace
  catalog_name = databricks_catalog.dev.id
  name         = "devdb"
  comment      = "this database is for dev team"
  properties = {
    kind = "various"
  }
}

resource "databricks_grants" "dev_database_grants" {
  provider = databricks.workspace
  schema   = databricks_schema.dev_database.id
  grant {
    principal  = var.group_name2
    privileges = ["USE_SCHEMA"]
  }
  grant {
    principal  = var.databricks_admin_user
    privileges = ["USE_SCHEMA"]
  }
  depends_on = [
    databricks_mws_permission_assignment.add_non_admin_group,
    databricks_mws_permission_assignment.add_admin_group,
    databricks_grants.all_grants
  ]
}

/*
https://docs.gcp.databricks.com/data-governance/unity-catalog/manage-external-locations-and-credentials.html
- Create GCS storage to be used as an external storage location
- Create Databricks storage account credential (databricks managed GSA)
- Assign permision to GSA on GCS storage account
- Register storage location with unity as an external storage location
- Grant permission to groups/users on external storage credential
*/



// Configure external tables and credentials
// https://registry.terraform.io/providers/databricks/databricks/latest/docs/guides/unity-catalog-gcp#configure-external-tables-and-credentials

resource "google_storage_bucket" "ext_bucket" {
  name          = "${var.external_storage}-${var.google_region}-${random_string.databricks_suffix.result}"
  location      = var.google_region
  force_destroy = true
}

// https://docs.gcp.databricks.com/data-governance/unity-catalog/manage-external-locations-and-credentials.html#create-a-storage-credential

resource "databricks_storage_credential" "external_storage1_credential" {
  provider     = databricks.accounts
  metastore_id = databricks_metastore.this.id
  name         = "${var.external_storage}-${var.google_region}-${random_string.databricks_suffix.result}-creds"
  databricks_gcp_service_account {}
  depends_on = [
    databricks_metastore_assignment.this,
    databricks_grants.all_grants
  ]
}

resource "google_storage_bucket_iam_member" "unity_cred_admin" {
  bucket = google_storage_bucket.ext_bucket.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${databricks_storage_credential.external_storage1_credential.databricks_gcp_service_account[0].email}"
}

resource "google_storage_bucket_iam_member" "unity_cred_reader" {
  bucket = google_storage_bucket.ext_bucket.name
  role   = "roles/storage.legacyBucketReader"
  member = "serviceAccount:${databricks_storage_credential.external_storage1_credential.databricks_gcp_service_account[0].email}"
}

// Grant permission to a group on external storage credentials 
resource "databricks_grants" "external_storage1_credential_grants" {
  provider           = databricks.workspace
  storage_credential = databricks_storage_credential.external_storage1_credential.id
  grant {
    principal  = var.group_name1
    privileges = ["CREATE_EXTERNAL_TABLE", "READ_FILES", "WRITE_FILES"]
  }
  grant {
    principal  = var.databricks_admin_user
    privileges = ["ALL_PRIVILEGES"]
  }
  depends_on = [
    databricks_mws_permission_assignment.add_non_admin_group,
    databricks_mws_permission_assignment.add_admin_group,
    databricks_grants.all_grants
  ]
}

// Create external storage location and assign external storage credential
// https://docs.gcp.databricks.com/data-governance/unity-catalog/manage-external-locations-and-credentials.html#create-an-external-location

resource "databricks_external_location" "external_storage1" {
  provider = databricks.workspace
  name     = "the-ext-location"
  url      = "gs://${google_storage_bucket.ext_bucket.name}"

  credential_name = databricks_storage_credential.external_storage1_credential.id
  comment         = "external storage location for projectA"
  depends_on = [
    databricks_metastore_assignment.this,
    google_storage_bucket_iam_member.unity_cred_reader,
    google_storage_bucket_iam_member.unity_cred_admin,
    databricks_grants.all_grants
  ]
}

resource "databricks_grants" "external_storage1_grant" {
  provider          = databricks.workspace
  external_location = databricks_external_location.external_storage1.id
  grant {
    principal  = var.databricks_admin_user
    privileges = ["ALL_PRIVILEGES"]
  }
  depends_on = [
    databricks_mws_permission_assignment.add_non_admin_group,
    databricks_mws_permission_assignment.add_admin_group,
    databricks_grants.all_grants
  ]
}