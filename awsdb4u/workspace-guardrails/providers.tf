# Databricks unified authentication: an account-admin service principal
# (export DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET) or a CLI
# profile (export DATABRICKS_CONFIG_PROFILE). Nothing is stored in files.

provider "databricks" {
  alias      = "accounts"
  host       = var.databricks_account_console_url
  account_id = var.databricks_account_id
}

provider "databricks" {
  alias = "workspace"
  host  = var.workspace_url
}
