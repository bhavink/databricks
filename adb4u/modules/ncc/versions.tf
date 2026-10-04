terraform {
  required_version = ">= 1.5"

  required_providers {
    databricks = {
      source                = "databricks/databricks"
      version               = ">= 1.81" # databricks_account_network_policy, databricks_workspace_network_option
      configuration_aliases = [databricks.account]
    }
  }
}
