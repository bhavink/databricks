***REMOVED*** ==============================================
***REMOVED*** Required Configuration
***REMOVED*** ==============================================

variable "workspace_prefix" {
  description = "Prefix for resource naming (lowercase alphanumeric, max 12 chars)"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{1,12}$", var.workspace_prefix))
    error_message = "workspace_prefix must be lowercase alphanumeric, max 12 characters"
  }
}

variable "random_suffix" {
  description = "Random suffix for unique resource naming (4 characters)"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{4}$", var.random_suffix))
    error_message = "random_suffix must be 4 lowercase alphanumeric characters"
  }
}

variable "location" {
  description = "Azure region for Service Endpoint Policy"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name for Service Endpoint Policy"
  type        = string
}

***REMOVED*** ==============================================
***REMOVED*** Storage Account Resource IDs
***REMOVED*** ==============================================

variable "dbfs_storage_resource_id" {
  description = "DBFS storage account resource ID (always required)"
  type        = string

  validation {
    condition     = can(regex("^/subscriptions/.+/resourceGroups/.+/providers/Microsoft.Storage/storageAccounts/.+$", var.dbfs_storage_resource_id))
    error_message = "Must be a valid Azure storage account resource ID"
  }
}

variable "uc_metastore_storage_resource_id" {
  description = "Unity Catalog metastore storage account resource ID (empty if not creating metastore)"
  type        = string
  default     = ""

  validation {
    condition     = var.uc_metastore_storage_resource_id == "" || can(regex("^/subscriptions/.+/resourceGroups/.+/providers/Microsoft.Storage/storageAccounts/.+$", var.uc_metastore_storage_resource_id))
    error_message = "Must be empty or a valid Azure storage account resource ID"
  }
}

variable "uc_external_storage_resource_id" {
  description = "Unity Catalog external location storage account resource ID (empty if not creating)"
  type        = string
  default     = ""

  validation {
    condition     = var.uc_external_storage_resource_id == "" || can(regex("^/subscriptions/.+/resourceGroups/.+/providers/Microsoft.Storage/storageAccounts/.+$", var.uc_external_storage_resource_id))
    error_message = "Must be empty or a valid Azure storage account resource ID"
  }
}

variable "additional_storage_ids" {
  description = "Additional customer storage account resource IDs to allow (e.g., existing data lakes, backup storage)"
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for id in var.additional_storage_ids : can(regex("^/subscriptions/.+/resourceGroups/.+/providers/Microsoft.Storage/storageAccounts/.+$", id))
    ])
    error_message = "All entries must be valid Azure storage account resource IDs"
  }
}

***REMOVED*** ==============================================
***REMOVED*** Tags
***REMOVED*** ==============================================

variable "tags" {
  description = "Tags to apply to Service Endpoint Policy"
  type        = map(string)
  default     = {}
}
