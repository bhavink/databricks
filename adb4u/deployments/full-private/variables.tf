***REMOVED*** ==============================================
***REMOVED*** Core Configuration
***REMOVED*** ==============================================

variable "workspace_prefix" {
  description = "Prefix for resource naming (lowercase alphanumeric, max 12 chars). Used in all resource names."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{1,12}$", var.workspace_prefix))
    error_message = "workspace_prefix must be lowercase alphanumeric, max 12 characters"
  }
}

variable "location" {
  description = "Azure region for all resources (e.g., eastus2, westus, centralus)"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the Azure resource group where all resources will be created"
  type        = string
}

***REMOVED*** ==============================================
***REMOVED*** Databricks Account Configuration
***REMOVED*** ==============================================

variable "databricks_account_id" {
  description = "Databricks Account ID (format: 12345678-1234-1234-1234-123456789012)"
  type        = string

  validation {
    condition     = can(regex("^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", var.databricks_account_id))
    error_message = "databricks_account_id must be a valid UUID"
  }
}

***REMOVED*** ==============================================
***REMOVED*** Network Configuration (BYOV or Create New)
***REMOVED*** ==============================================

variable "use_existing_network" {
  description = "Use existing VNet/Subnets/NSG (true) or create new (false). When true, ALL network resources must exist."
  type        = bool
  default     = false
}

***REMOVED*** Existing Network (BYOV)
variable "existing_vnet_name" {
  description = "Name of existing VNet (required if use_existing_network=true)"
  type        = string
  default     = ""
}

variable "existing_resource_group_name" {
  description = "Resource group of existing VNet (required if use_existing_network=true)"
  type        = string
  default     = ""
}

variable "existing_public_subnet_name" {
  description = "Name of existing public/host subnet (required if use_existing_network=true)"
  type        = string
  default     = ""
}

variable "existing_private_subnet_name" {
  description = "Name of existing private/container subnet (required if use_existing_network=true)"
  type        = string
  default     = ""
}

variable "existing_privatelink_subnet_name" {
  description = "Name of existing Private Link subnet (required if use_existing_network=true for Full Private)"
  type        = string
  default     = ""
}

variable "existing_nsg_name" {
  description = "Name of existing NSG (required if use_existing_network=true)"
  type        = string
  default     = ""
}

***REMOVED*** New Network Configuration
variable "vnet_address_space" {
  description = "Address space for VNet (CIDR /16 to /24). Used when creating new VNet."
  type        = list(string)
  default     = ["10.178.0.0/20"]
}

variable "public_subnet_address_prefix" {
  description = "Address prefix for public/host subnet (CIDR at least /26). Used when creating new subnet."
  type        = list(string)
  default     = ["10.178.0.0/26"]
}

variable "private_subnet_address_prefix" {
  description = "Address prefix for private/container subnet (CIDR at least /26). Used when creating new subnet."
  type        = list(string)
  default     = ["10.178.1.0/26"]
}

variable "privatelink_subnet_address_prefix" {
  description = "Address prefix for Private Link subnet (CIDR at least /27). Used when creating new subnet for Full Private pattern."
  type        = list(string)
  default     = ["10.178.2.0/27"]
}

***REMOVED*** ==============================================
***REMOVED*** Network Connectivity Configuration (NCC)
***REMOVED*** ==============================================

variable "enable_ncc" {
  description = "Enable Network Connectivity Configuration (NCC) for Databricks Serverless compute. Requires manual approval of Private Endpoint connections in Azure Portal. Set to false for initial deployment, enable later if serverless is needed."
  type        = bool
  default     = false
}

***REMOVED*** ==============================================
***REMOVED*** Unity Catalog Configuration
***REMOVED*** ==============================================

variable "create_metastore" {
  description = "Create new Unity Catalog metastore (true) or use existing (false). Metastores are regional - create one for first workspace, reuse for subsequent workspaces in same region."
  type        = bool
  default     = true
}

variable "existing_metastore_id" {
  description = "Existing Unity Catalog metastore ID (required if create_metastore=false)"
  type        = string
  default     = ""
}

variable "metastore_name" {
  description = "Name for Unity Catalog metastore (e.g., prod-eastus2-metastore). Ignored if create_metastore=false."
  type        = string
  default     = ""
}

***REMOVED*** Access Connector Configuration
variable "create_access_connector" {
  description = "Create new Access Connector (true) or use existing (false). Recommended: one per workspace for isolation."
  type        = bool
  default     = true
}

variable "existing_access_connector_id" {
  description = "Existing Access Connector resource ID (required if create_access_connector=false)"
  type        = string
  default     = ""
}

variable "existing_access_connector_principal_id" {
  description = "Existing Access Connector principal ID (required if create_access_connector=false)"
  type        = string
  default     = ""
}

***REMOVED*** Storage Account Name Prefixes (Optional)
variable "metastore_storage_name_prefix" {
  description = "Custom name prefix for Unity Catalog metastore root storage account (lowercase alphanumeric, max 18 chars). If empty, defaults to '{workspace_prefix}metastore'. Random suffix will be added."
  type        = string
  default     = ""
}

variable "external_storage_name_prefix" {
  description = "Custom name prefix for Unity Catalog external location storage account (lowercase alphanumeric, max 18 chars). If empty, defaults to '{workspace_prefix}external'. Random suffix will be added."
  type        = string
  default     = ""
}

***REMOVED*** ==============================================
***REMOVED*** Customer-Managed Keys (CMK) - Optional
***REMOVED*** ==============================================

variable "enable_cmk_managed_services" {
  description = "Enable CMK for Databricks managed services (notebooks, secrets). Requires cmk_key_vault_key_id."
  type        = bool
  default     = true  ***REMOVED*** Enabled by default for Full Private
}

variable "enable_cmk_managed_disks" {
  description = "Enable CMK for managed disks (cluster VM disks). Requires cmk_key_vault_key_id and cmk_key_vault_id."
  type        = bool
  default     = true  ***REMOVED*** Enabled by default for Full Private
}

variable "enable_cmk_dbfs_root" {
  description = "Enable CMK for DBFS root storage. Requires cmk_key_vault_key_id."
  type        = bool
  default     = true  ***REMOVED*** Enabled by default for Full Private
}

variable "cmk_key_vault_key_id" {
  description = "Azure Key Vault Key ID for CMK encryption (e.g., https://kv-name.vault.azure.net/keys/key-name/version). Required if any enable_cmk_* is true."
  type        = string
  default     = ""
}

variable "cmk_key_vault_id" {
  description = "Azure Key Vault resource ID for Disk Encryption Set. Required if enable_cmk_managed_disks=true."
  type        = string
  default     = ""
}

***REMOVED*** ==============================================
***REMOVED*** Network Access Control
***REMOVED*** ==============================================

variable "enable_public_network_access" {
  description = "Enable public network access to the workspace. Set to 'true' for initial deployment from outside VNet, then set to 'false' to lock down to Private Link only (air-gapped)."
  type        = bool
  default     = true
}

***REMOVED*** ==============================================
***REMOVED*** IP Access Lists - Optional
***REMOVED*** ==============================================

variable "enable_ip_access_lists" {
  description = "Enable IP Access Lists to restrict workspace access by source IP. Recommended for additional security."
  type        = bool
  default     = false
}

variable "allowed_ip_ranges" {
  description = "List of allowed IP ranges in CIDR notation (e.g., ['203.0.113.0/24']). Required if enable_ip_access_lists=true."
  type        = list(string)
  default     = []
}

***REMOVED*** ==============================================
***REMOVED*** Resource Tagging
***REMOVED*** ==============================================

variable "tags" {
  description = "Tags to apply to all resources (e.g., {Environment = 'Production', Project = 'DataPlatform'})"
  type        = map(string)
  default     = {}
}

variable "tag_owner" {
  description = "Owner tag value (e.g., email address or team name). Added to all resources."
  type        = string
}

variable "tag_keepuntil" {
  description = "Keep until date tag value (e.g., '12/31/2026'). Used for lifecycle management."
  type        = string
}
