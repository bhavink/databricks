***REMOVED*** ==============================================
***REMOVED*** Metastore Configuration
***REMOVED*** ==============================================

variable "create_metastore" {
  description = "Create new Unity Catalog metastore (true) or use existing (false)"
  type        = bool
  default     = true
}

variable "existing_metastore_id" {
  description = "Existing metastore ID (required if create_metastore=false)"
  type        = string
  default     = ""
}

variable "metastore_name" {
  description = "Name of the Unity Catalog metastore (used only when create_metastore=true)"
  type        = string
  default     = ""
}

variable "databricks_account_id" {
  description = "Databricks account ID (required for metastore operations)"
  type        = string

  validation {
    condition     = can(regex("^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", var.databricks_account_id))
    error_message = "databricks_account_id must be a valid UUID"
  }
}

***REMOVED*** ==============================================
***REMOVED*** Storage Account Naming (Optional)
***REMOVED*** ==============================================

variable "metastore_storage_name_prefix" {
  description = "Custom name prefix for metastore storage account (lowercase alphanumeric, max 18 chars). If empty, uses '{workspace_prefix}metastore'. Random suffix will be appended."
  type        = string
  default     = ""
}

variable "external_storage_name_prefix" {
  description = "Custom name prefix for external location storage account (lowercase alphanumeric, max 18 chars). If empty, uses '{workspace_prefix}external'. Random suffix will be appended."
  type        = string
  default     = ""
}

***REMOVED*** ==============================================
***REMOVED*** Workspace Configuration
***REMOVED*** ==============================================

variable "workspace_id" {
  description = "Databricks workspace ID to attach to metastore"
  type        = string
}

variable "workspace_prefix" {
  description = "Prefix for resource naming"
  type        = string
}

***REMOVED*** ==============================================
***REMOVED*** Storage Configuration
***REMOVED*** ==============================================

variable "location" {
  description = "Azure region for Unity Catalog resources"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name for Unity Catalog resources"
  type        = string
}

variable "create_metastore_storage" {
  description = "Create metastore root storage account (true) or skip if using existing metastore (false)"
  type        = bool
  default     = true
}

variable "create_external_location_storage" {
  description = "Create external location storage account for workspace data"
  type        = bool
  default     = true
}

***REMOVED*** ==============================================
***REMOVED*** Access Connector Configuration
***REMOVED*** ==============================================

variable "create_access_connector" {
  description = "Create new Access Connector (true) or use existing (false)"
  type        = bool
  default     = true
}

variable "existing_access_connector_id" {
  description = "Existing Access Connector resource ID (required if create_access_connector=false)"
  type        = string
  default     = ""
}

variable "existing_access_connector_principal_id" {
  description = "Principal ID of existing Access Connector (required if create_access_connector=false)"
  type        = string
  default     = ""
}

***REMOVED*** ==============================================
***REMOVED*** Storage Connectivity (PL vs SEP)
***REMOVED*** ==============================================

variable "enable_private_link_storage" {
  description = "Enable Private Link for Unity Catalog storage accounts. Default is Service Endpoints."
  type        = bool
  default     = false
}

variable "storage_private_endpoint_subnet_id" {
  description = "Subnet ID for storage private endpoints (required if enable_private_link_storage=true)"
  type        = string
  default     = ""
}

variable "service_endpoints_enabled" {
  description = "Service endpoints are enabled on subnets (required for SEP connectivity)"
  type        = bool
  default     = true
}

***REMOVED*** ==============================================
***REMOVED*** Service Endpoint Policies (SEP)
***REMOVED*** ==============================================

variable "enable_service_endpoint_policies" {
  description = "Create Service Endpoint Policies for storage security"
  type        = bool
  default     = true
}

***REMOVED*** ==============================================
***REMOVED*** Additional Configuration
***REMOVED*** ==============================================

variable "external_location_name" {
  description = "Name of the external location (defaults to workspace-prefix-external)"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags to apply to all Unity Catalog resources"
  type        = map(string)
  default     = {}
}
