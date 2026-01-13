***REMOVED*** ==============================================
***REMOVED*** Service Endpoint Policy for Storage Egress Control
***REMOVED*** ==============================================
***REMOVED***
***REMOVED*** Purpose: Restricts VNet egress to only allow-listed storage accounts
***REMOVED*** Scope: Classic compute only (not applicable to serverless)
***REMOVED*** Security: Prevents data exfiltration via unauthorized storage access
***REMOVED***
***REMOVED*** Reference: https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/service-endpoints
***REMOVED***
***REMOVED*** IMPORTANT: Workspace Requirement
***REMOVED*** ---------------------------------
***REMOVED*** Workspaces created on or after July 14, 2025 support SEP by default.
***REMOVED*** For workspaces created BEFORE July 14, 2025:
***REMOVED***   - Contact your Databricks account team to enable SEP support for your workspace
***REMOVED***   - Without this enablement, Azure API will reject the /services/Azure/Databricks alias
***REMOVED***   - Error: "ServiceResourceNameMustHaveEvenElements: invalid resource name"
***REMOVED***
***REMOVED*** Once enabled, the /services/Azure/Databricks alias allows access to Databricks-managed
***REMOVED*** storage accounts (artifacts, logs, DBR images, system tables) without needing specific
***REMOVED*** resource IDs from Databricks' managed subscriptions.
***REMOVED***

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

***REMOVED*** ==============================================
***REMOVED*** Service Endpoint Policy Resource
***REMOVED*** ==============================================

resource "azurerm_subnet_service_endpoint_storage_policy" "this" {
  name                = "${var.workspace_prefix}-sep-storage-${var.random_suffix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags

  ***REMOVED*** Definition 1: Databricks System Storage (REQUIRED)
  ***REMOVED*** ---------------------------------------------------
  ***REMOVED*** Managed by Databricks in Databricks-owned Azure subscriptions
  ***REMOVED*** Includes: Artifact Blob, Log Blob, DBR Container Registry, System Tables
  ***REMOVED*** 
  ***REMOVED*** The /services/Azure/Databricks alias is a special service resource identifier
  ***REMOVED*** that grants access to all Databricks-managed storage without needing specific
  ***REMOVED*** resource IDs (which customers don't have access to).
  ***REMOVED***
  ***REMOVED*** IMPORTANT: Service aliases must use service = "Global", not "Microsoft.Storage"
  ***REMOVED***
  ***REMOVED*** Reference: https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/service-endpoints***REMOVED***step-1-create-a-service-endpoint-policy
  definition {
    name        = "databricks-system-storage"
    description = "Allow access to Databricks-managed system storage (artifacts, logs, DBR images, system tables)"
    service     = "Global"  ***REMOVED*** Required for service aliases
    service_resources = [
      "/services/Azure/Databricks" ***REMOVED*** Special alias for Databricks-managed storage
    ]
  }

  ***REMOVED*** Definition 2: Customer Storage Accounts
  ***REMOVED*** ----------------------------------------
  ***REMOVED*** Customer-owned storage in customer's Azure subscription
  ***REMOVED*** Dynamically built based on what's created/provided
  definition {
    name        = "customer-storage-accounts"
    description = "Allow access to customer-managed storage (DBFS, Unity Catalog, custom)"
    service     = "Microsoft.Storage"
    service_resources = concat(
      ***REMOVED*** Always include DBFS storage
      [var.dbfs_storage_resource_id],

      ***REMOVED*** Conditionally include UC Metastore storage if created
      var.uc_metastore_storage_resource_id != "" ? [var.uc_metastore_storage_resource_id] : [],

      ***REMOVED*** Conditionally include UC External storage if created
      var.uc_external_storage_resource_id != "" ? [var.uc_external_storage_resource_id] : [],

      ***REMOVED*** Include any additional customer-provided storage accounts
      var.additional_storage_ids
    )
  }
}
