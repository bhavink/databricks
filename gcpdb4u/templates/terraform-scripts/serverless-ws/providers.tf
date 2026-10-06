# Same authentication as the other gcpdb4u roots: impersonate the automation
# service account (export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)
# or rely on gcloud application-default credentials).

provider "databricks" {
  alias                  = "accounts"
  host                   = var.databricks_account_console_url
  account_id             = var.databricks_account_id
  google_service_account = var.google_service_account_email
}
