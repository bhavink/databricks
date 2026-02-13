# ==============================================
# Service Endpoint Policy for Storage Egress Control
# ==============================================
#
# Purpose: Restricts VNet egress to only allow-listed storage accounts
# Scope: Classic compute only (not applicable to serverless)
# Security: Prevents data exfiltration via unauthorized storage access
#
# Reference: https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/service-endpoints
#
# IMPORTANT: Workspace Requirement
# ---------------------------------
# Workspaces created on or after July 14, 2025 support SEP by default.
# For workspaces created BEFORE July 14, 2025:
#   - Contact your Databricks account team to enable SEP support for your workspace
#   - Without this enablement, Azure API will reject the /services/Azure/Databricks alias
#   - Error: "ServiceResourceNameMustHaveEvenElements: invalid resource name"
#
# Once enabled, the /services/Azure/Databricks alias allows access to Databricks-managed
# storage accounts (artifacts, logs, DBR images, system tables) without needing specific
# resource IDs from Databricks' managed subscriptions.
#

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

# ==============================================
# Service Endpoint Policy Resource
# ==============================================

resource "azurerm_subnet_service_endpoint_storage_policy" "this" {
  name                = "${var.workspace_prefix}-sep-storage-${var.random_suffix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags

  # Definition 1: Databricks System Storage (REQUIRED)
  # ---------------------------------------------------
  # Managed by Databricks in Databricks-owned Azure subscriptions
  # Includes: Artifact Blob, Log Blob, DBR Container Registry, System Tables
  # 
  # The /services/Azure/Databricks alias is a special service resource identifier
  # that grants access to all Databricks-managed storage without needing specific
  # resource IDs (which customers don't have access to).
  #
  # IMPORTANT: Service aliases must use service = "Global", not "Microsoft.Storage"
  #
  # Reference: https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/service-endpoints#step-1-create-a-service-endpoint-policy
  definition {
    name        = "databricks-system-storage"
    description = "Allow access to Databricks-managed system storage (artifacts, logs, DBR images, system tables)"
    service     = "Global"  # Required for service aliases
    service_resources = [
      "/services/Azure/Databricks" # Special alias for Databricks-managed storage
    ]
  }

  # Definition 2: Customer Storage Accounts
  # ----------------------------------------
  # Customer-owned storage in customer's Azure subscription
  # Dynamically built based on what's created/provided
  definition {
    name        = "customer-storage-accounts"
    description = "Allow access to customer-managed storage (DBFS, Unity Catalog, custom)"
    service     = "Microsoft.Storage"
    service_resources = concat(
      # Always include DBFS storage
      [var.dbfs_storage_resource_id],

      # Conditionally include UC Metastore storage if created
      var.uc_metastore_storage_resource_id != "" ? [var.uc_metastore_storage_resource_id] : [],

      # Conditionally include UC External storage if created
      var.uc_external_storage_resource_id != "" ? [var.uc_external_storage_resource_id] : [],

      # Include any additional customer-provided storage accounts
      var.additional_storage_ids
    )
  }
}
