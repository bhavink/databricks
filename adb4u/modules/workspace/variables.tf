***REMOVED*** ==============================================
***REMOVED*** Workspace Configuration
***REMOVED*** ==============================================

variable "workspace_name" {
  description = "Name of the Databricks workspace"
  type        = string
}

variable "workspace_prefix" {
  description = "Prefix for resource naming (used for managed resource group)"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name for workspace"
  type        = string
}

variable "location" {
  description = "Azure region for workspace"
  type        = string
}

***REMOVED*** ==============================================
***REMOVED*** Network Configuration
***REMOVED*** ==============================================

variable "vnet_id" {
  description = "Virtual Network ID for VNet injection"
  type        = string
}

variable "public_subnet_name" {
  description = "Public/host subnet name"
  type        = string
}

variable "private_subnet_name" {
  description = "Private/container subnet name"
  type        = string
}

variable "public_subnet_nsg_association_id" {
  description = "Public subnet NSG association ID"
  type        = string
}

variable "private_subnet_nsg_association_id" {
  description = "Private subnet NSG association ID"
  type        = string
}

variable "enable_private_link" {
  description = "Enable Private Link for workspace (front-end UI/API + back-end data plane). When true, public_network_access_enabled is set to false."
  type        = bool
  default     = false
}

***REMOVED*** ==============================================
***REMOVED*** Customer-Managed Keys (Optional)
***REMOVED*** ==============================================

variable "enable_cmk_managed_services" {
  description = "Enable CMK for control plane data (notebooks, secrets, queries)"
  type        = bool
  default     = false
}

variable "enable_cmk_managed_disks" {
  description = "Enable CMK for cluster VM managed disks"
  type        = bool
  default     = false
}

variable "enable_cmk_dbfs_root" {
  description = "Enable CMK for workspace DBFS root storage"
  type        = bool
  default     = false
}

variable "cmk_key_vault_key_id" {
  description = "Azure Key Vault key ID for CMK (required if any CMK enabled)"
  type        = string
  default     = ""
}

variable "cmk_key_vault_id" {
  description = "Azure Key Vault ID (required if enable_cmk_managed_disks=true)"
  type        = string
  default     = ""
}

variable "databricks_account_id" {
  description = "Databricks account ID (required for CMK)"
  type        = string
  default     = ""
}

***REMOVED*** ==============================================
***REMOVED*** IP Access Lists (Optional)
***REMOVED*** ==============================================

variable "enable_ip_access_lists" {
  description = "Enable workspace IP access list restrictions"
  type        = bool
  default     = false
}

variable "allowed_ip_ranges" {
  description = "List of allowed IP ranges in CIDR notation (e.g., ['203.0.113.0/24']). Required if enable_ip_access_lists=true."
  type        = list(string)
  default     = []
}

***REMOVED*** ==============================================
***REMOVED*** Additional Configuration
***REMOVED*** ==============================================

variable "additional_workspace_config" {
  description = "Additional workspace configuration settings (key-value map)"
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Tags to apply to workspace resource"
  type        = map(string)
  default     = {}
}
