***REMOVED*** ==============================================================================
***REMOVED*** Provider Configuration
***REMOVED*** ==============================================================================
***REMOVED*** Version requirements are defined in versions.tf
***REMOVED***
***REMOVED*** Authentication Methods for Google Provider:
***REMOVED*** 1. Application Default Credentials (recommended for CI/CD)
***REMOVED***    - Run: gcloud auth application-default login (for local development)
***REMOVED***    - Or use Workload Identity in GKE/Cloud Build
***REMOVED*** 2. Service account impersonation via google_service_account parameter
***REMOVED*** 3. Service account key file:
***REMOVED***    - Via GOOGLE_APPLICATION_CREDENTIALS environment variable
***REMOVED***    - Or via google_credentials parameter (path to key.json file)
***REMOVED***    - Not recommended for production - use ADC or impersonation instead
***REMOVED***
***REMOVED*** Example with google_credentials:
***REMOVED***   provider "google" {
***REMOVED***     credentials = "/path/to/service-account-key.json"  ***REMOVED*** or file(var.credentials_path)
***REMOVED***     project     = var.google_project_name
***REMOVED***     region      = var.google_region
***REMOVED***   }
***REMOVED***
***REMOVED*** Authentication Methods for Databricks Provider:
***REMOVED*** 1. Service account impersonation via google_service_account parameter (used here)
***REMOVED*** 2. Service account key file via google_credentials parameter (path to key.json)
***REMOVED*** 3. OAuth tokens (for interactive use)

provider "google" {
  alias   = "internal"
  project = var.google_project_name
  region  = var.google_region
}

***REMOVED*** COMMENTED OUT: googleworkspace provider (requires additional permissions)
***REMOVED*** REQUIRED PERMISSION: ccc.hosted.frontend.directory.v1.DirectoryMembers.Insert
***REMOVED*** REQUIREMENTS:
***REMOVED***   1. Terraform runs as a GSA
***REMOVED***   2. That GSA has domain-wide delegation enabled
***REMOVED***   3. The GSA impersonates a Workspace admin user
***REMOVED***   4. The API call is authorized as the admin user
***REMOVED*** TO ENABLE: Uncomment after configuring the above requirements
***REMOVED*** provider "googleworkspace" {
***REMOVED***   customer_id = var.google_workspace_customer_id
***REMOVED*** }

provider "google" {
  alias   = "external"
  project = var.external_project ? var.bucket_project_id : "null"
  region  = var.google_region
}



provider "databricks" {
  alias                  = "accounts"
  host                   = local.databricks_account_url
  account_id             = local.databricks_account_id
  google_service_account = var.databricks_google_service_account
}

provider "databricks" {
  alias                  = "workspace"
  host                   = databricks_mws_workspaces.dbx_workspace.workspace_url
  google_service_account = var.databricks_google_service_account
}
