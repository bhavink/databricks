# ==============================================
# Deployment Mode (Master Control)
# ==============================================

variable "use_byor_infrastructure" {
  description = "Set to true to use network and CMK resources provisioned by the BYOR deployment. When true, existing_* network and CMK variables must be provided. When false, new network and CMK resources will be created based on other variables."
  type        = bool
  default     = false
}

# ==============================================
# Core Configuration
# ==============================================

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

# ==============================================
# Databricks Account Configuration
# ==============================================

variable "databricks_account_id" {
  description = "Databricks Account ID (format: 12345678-1234-1234-1234-123456789012)"
  type        = string

  validation {
    condition     = can(regex("^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", var.databricks_account_id))
    error_message = "databricks_account_id must be a valid UUID"
  }
}

# ==============================================
# Network Configuration (BYOV or Create New)
# ==============================================

variable "use_existing_network" {
  description = "Use existing VNet/Subnets/NSG (true) or create new (false). When true, ALL network resources must exist."
  type        = bool
  default     = false
}

# Existing Network (BYOV)
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

variable "existing_public_subnet_nsg_association_id" {
  description = "Resource ID of the existing public subnet's NSG association (required if use_byor_infrastructure=true)"
  type        = string
  default     = ""
}

variable "existing_private_subnet_nsg_association_id" {
  description = "Resource ID of the existing private subnet's NSG association (required if use_byor_infrastructure=true)"
  type        = string
  default     = ""
}

# New Network Configuration
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

variable "enable_nat_gateway" {
  description = "Create NAT Gateway for egress. For Full Private (air-gapped), set to false. Only relevant when use_byor_infrastructure=false."
  type        = bool
  default     = false # Disabled by default for Full Private
}

# ==============================================
# Network Connectivity Configuration (NCC)
# ==============================================

variable "enable_ncc" {
  description = "Enable Network Connectivity Configuration (NCC) for Databricks Serverless compute. Requires manual approval of Private Endpoint connections in Azure Portal. Set to false for initial deployment, enable later if serverless is needed."
  type        = bool
  default     = false
}

# ==============================================
# Service Endpoint Policy (SEP) - Optional
# ==============================================

variable "enable_service_endpoint_policy" {
  description = "Enable Service Endpoint Policy for storage egress control (classic compute only). Restricts VNet storage access to allow-listed accounts only."
  type        = bool
  default     = true # Enabled by default
}

variable "additional_allowed_storage_ids" {
  description = "Additional customer storage account resource IDs to allow in SEP (e.g., existing data lakes, backup storage)"
  type        = list(string)
  default     = []
}

# ==============================================
# Unity Catalog Configuration
# ==============================================

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

# Access Connector Configuration
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

# Storage Account Name Prefixes (Optional)
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

# ==============================================
# Customer-Managed Keys (CMK) - Optional
# ==============================================

variable "enable_cmk_managed_services" {
  description = "Enable CMK for Databricks managed services (notebooks, secrets). Requires cmk_key_vault_key_id."
  type        = bool
  default     = true # Enabled by default for Full Private
}

variable "enable_cmk_managed_disks" {
  description = "Enable CMK for managed disks (cluster VM disks). Requires cmk_key_vault_key_id and cmk_key_vault_id."
  type        = bool
  default     = true # Enabled by default for Full Private
}

variable "enable_cmk_dbfs_root" {
  description = "Enable CMK for DBFS root storage. Requires cmk_key_vault_key_id."
  type        = bool
  default     = true # Enabled by default for Full Private
}

# Key Vault Configuration (Create or Bring)
variable "create_key_vault" {
  description = "Create new Key Vault (true) or use existing (false). When use_byor_infrastructure=true with CMK enabled, this is automatically set to false."
  type        = bool
  default     = true
}

variable "existing_key_vault_id" {
  description = "Azure Key Vault resource ID (required if create_key_vault=false or use_byor_infrastructure=true with CMK)"
  type        = string
  default     = ""
}

variable "existing_key_id" {
  description = "Azure Key Vault key ID (optional, will create if not provided)"
  type        = string
  default     = ""
}

variable "cmk_key_vault_key_id" {
  description = "Azure Key Vault Key ID for CMK encryption (e.g., https://kv-name.vault.azure.net/keys/key-name/version). Required if any enable_cmk_* is true. Auto-populated from Key Vault module or use existing_key_id."
  type        = string
  default     = ""
}

variable "cmk_key_vault_id" {
  description = "Azure Key Vault resource ID for Disk Encryption Set. Required if enable_cmk_managed_disks=true."
  type        = string
  default     = ""
}

# ==============================================
# Network Access Control
# ==============================================

variable "enable_public_network_access" {
  description = "Enable public network access to the workspace. Set to 'true' for initial deployment from outside VNet, then set to 'false' to lock down to Private Link only (air-gapped)."
  type        = bool
  default     = true
}

# ==============================================
# IP Access Lists - Optional
# ==============================================

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

# ==============================================
# Resource Tagging
# ==============================================

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
