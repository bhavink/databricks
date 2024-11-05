variable "subscription_id" {}
variable "databricks_account_id" {}

terraform {
  required_providers {
    azurerm = {
      source = "hashicorp/azurerm"
    }
    databricks = {
      source = "databricks/databricks"
    }
  }
}

provider "azurerm" {
  subscription_id = var.subscription_id
  features {}
}

provider "databricks" {
  host = azurerm_databricks_workspace.this.workspace_url
}

provider "databricks" {
  alias      = "accounts"
  host       = "https://accounts.staging.azuredatabricks.net"
  account_id = var.databricks_account_id
}

