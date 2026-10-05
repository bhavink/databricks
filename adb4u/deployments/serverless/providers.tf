# ==============================================
# Azure Providers
# ==============================================
# Authentication (in order of precedence):
# 1. Environment variables (RECOMMENDED): ARM_CLIENT_ID, ARM_CLIENT_SECRET,
#    ARM_TENANT_ID, ARM_SUBSCRIPTION_ID
# 2. Azure CLI: az login (for development)

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

# The workspace is created through the ARM API (azapi): azurerm_databricks_workspace
# cannot set computeMode = "Serverless" yet.
provider "azapi" {}

# ==============================================
# Databricks Account Provider (default)
# ==============================================
# Account-level resources: metastore assignment, NCC, binding, network policy.
# Requires DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET and
# DATABRICKS_AZURE_TENANT_ID (or ARM_TENANT_ID).

provider "databricks" {
  host       = "https://accounts.azuredatabricks.net"
  account_id = var.databricks_account_id
}

# ==============================================
# Databricks Workspace Provider
# ==============================================
# Workspace-level settings (IP access lists, workspace configuration).
# The placeholder lets Terraform configure the provider before the
# workspace exists; resources using it run after workspace creation.

provider "databricks" {
  alias = "workspace"
  host  = try("https://${local.workspace_url}", "https://placeholder.azuredatabricks.net")
}
