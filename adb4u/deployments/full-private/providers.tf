# ==============================================
# Azure Provider Configuration
# ==============================================

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
  
  # Authentication (in order of precedence):
  # 1. Environment Variables (RECOMMENDED):
  #    - ARM_CLIENT_ID
  #    - ARM_CLIENT_SECRET
  #    - ARM_TENANT_ID
  #    - ARM_SUBSCRIPTION_ID
  # 2. Azure CLI: az login (for development)
  # 3. Managed Identity: ARM_USE_MSI=true (for Azure-hosted)
}

# ==============================================
# Databricks Workspace Provider
# ==============================================
# Used for workspace-level operations (IP Access Lists, workspace config, Unity Catalog storage credentials)
# Configured after workspace creation via workspace URL

provider "databricks" {
  alias = "workspace"
  host  = try(module.workspace.workspace_url, "https://placeholder.azuredatabricks.net")
  
  # Azure Authentication (reads from environment variables)
  # Required: DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET, DATABRICKS_AZURE_TENANT_ID
  
  # Note: During initial deployment, workspace URL doesn't exist yet.
  # The 'try' function provides a placeholder to allow provider configuration.
  # Resources using this provider will only execute after workspace creation.
}

# ==============================================
# Databricks Account Provider
# ==============================================
# Used for account-level operations (Unity Catalog metastore, NCC)
# Requires Databricks Account ID

provider "databricks" {
  alias      = "account"
  host       = "https://accounts.azuredatabricks.net"
  account_id = var.databricks_account_id
  
  # Authentication for Azure Databricks Account:
  # Requires environment variables:
  # - DATABRICKS_CLIENT_ID (Service Principal Application ID)
  # - DATABRICKS_CLIENT_SECRET (Service Principal Secret)
  # AND one of:
  # - DATABRICKS_AZURE_TENANT_ID (Azure AD Tenant ID) - RECOMMENDED
  # - ARM_TENANT_ID (Azure AD Tenant ID) - Alternative
  
  # These settings help the provider find the correct authentication
  azure_use_msi     = false  # We're using Service Principal, not Managed Identity
  azure_environment = "public"  # Azure Public Cloud
}
