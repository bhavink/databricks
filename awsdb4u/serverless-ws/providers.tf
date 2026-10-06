# Databricks unified authentication: an account-admin service principal
# (export DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET) or a CLI
# profile (export DATABRICKS_CONFIG_PROFILE). Nothing is stored in files.
# No AWS provider: a serverless workspace creates no AWS resources.

provider "databricks" {
  alias      = "accounts"
  host       = var.databricks_account_console_url
  account_id = var.databricks_account_id
}
