provider "azurerm" {
  features {}
}

provider "databricks" {
  alias      = "account"
  host       = "https://accounts.azuredatabricks.net"
  account_id = var.databricks_account_id

  ***REMOVED*** Force authentication via environment variables
  azure_use_msi      = false
  azure_environment  = "public"
}

provider "databricks" {
  alias = "workspace"
  host  = try(module.workspace.workspace_url, "")
}
