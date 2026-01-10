terraform {
  required_version = ">= 1.5"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.40"
      configuration_aliases = [databricks.account, databricks.workspace]
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}
