# ==============================================
# Azure Provider
# ==============================================

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

# ==============================================
# Databricks Workspace Provider (optional, for UC assignment)
# ==============================================
# Set when attaching to existing UC: use workspace URL (from output after first apply).
# Auth: Azure SP via DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET, DATABRICKS_AZURE_TENANT_ID.

provider "databricks" {
  host = coalesce(var.databricks_host, "https://placeholder.azuredatabricks.net")
}
