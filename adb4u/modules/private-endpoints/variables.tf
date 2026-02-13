# ==============================================
# Required Configuration
# ==============================================

variable "location" {
  description = "Azure region for Private Endpoints and DNS zones"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name for Private Endpoints"
  type        = string
}

variable "workspace_prefix" {
  description = "Prefix for resource naming (lowercase alphanumeric, max 12 chars)"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{1,12}$", var.workspace_prefix))
    error_message = "workspace_prefix must be lowercase alphanumeric, max 12 characters"
  }
}

variable "tags" {
  description = "Tags to apply to all Private Endpoint resources"
  type        = map(string)
  default     = {}
}

# ==============================================
# Network Configuration
# ==============================================

variable "vnet_id" {
  description = "Virtual Network ID for DNS zone links"
  type        = string
}

variable "privatelink_subnet_id" {
  description = "Private Link subnet ID where Private Endpoints will be deployed"
  type        = string
}

# ==============================================
# Workspace Configuration
# ==============================================

variable "workspace_id" {
  description = "Azure resource ID of the Databricks workspace"
  type        = string
}

variable "workspace_managed_resource_group_id" {
  description = "Managed resource group ID of the Databricks workspace (for DBFS storage)"
  type        = string
}

variable "dbfs_storage_name" {
  description = "DBFS storage account name (from workspace custom_parameters)"
  type        = string
}

# ==============================================
# Unity Catalog Storage Configuration
# ==============================================

variable "create_uc_metastore_storage" {
  description = "Whether Unity Catalog metastore storage is being created (determines if metastore Private Endpoints should be created)"
  type        = bool
  default     = true
}

variable "uc_metastore_storage_account_id" {
  description = "Resource ID of Unity Catalog metastore storage account (optional if using existing metastore)"
  type        = string
  default     = ""
}

variable "uc_external_storage_account_id" {
  description = "Resource ID of Unity Catalog external location storage account"
  type        = string
  default     = ""
}

variable "enable_uc_storage_private_endpoints" {
  description = "Create Private Endpoints for Unity Catalog storage accounts. If false, only Databricks (DP-CP/Auth) and DBFS Private Endpoints are created."
  type        = bool
  default     = true
}
