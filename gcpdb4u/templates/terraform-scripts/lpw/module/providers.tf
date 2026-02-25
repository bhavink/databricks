# ==============================================================================
# Provider Configuration
# ==============================================================================
# Version requirements are defined in versions.tf
#
# Authentication Methods for Google Provider:
# 1. Application Default Credentials (recommended for CI/CD)
#    - Run: gcloud auth application-default login (for local development)
#    - Or use Workload Identity in GKE/Cloud Build
# 2. Service account impersonation via google_service_account parameter
# 3. Service account key file:
#    - Via GOOGLE_APPLICATION_CREDENTIALS environment variable
#    - Or via google_credentials parameter (path to key.json file)
#    - Not recommended for production - use ADC or impersonation instead
#
# Example with google_credentials:
#   provider "google" {
#     credentials = "/path/to/service-account-key.json"  # or file(var.credentials_path)
#     project     = var.google_project_name
#     region      = var.google_region
#   }
#
# Authentication Methods for Databricks Provider:
# 1. Service account impersonation via google_service_account parameter (used here)
# 2. Service account key file via google_credentials parameter (path to key.json)
# 3. OAuth tokens (for interactive use)

provider "google" {
  alias   = "internal"
  project = var.google_project_name
  region  = var.google_region
}

# COMMENTED OUT: googleworkspace provider (requires additional permissions)
# REQUIRED PERMISSION: ccc.hosted.frontend.directory.v1.DirectoryMembers.Insert
# REQUIREMENTS:
#   1. Terraform runs as a GSA
#   2. That GSA has domain-wide delegation enabled
#   3. The GSA impersonates a Workspace admin user
#   4. The API call is authorized as the admin user
# TO ENABLE: Uncomment after configuring the above requirements
# provider "googleworkspace" {
#   customer_id = var.google_workspace_customer_id
# }

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
