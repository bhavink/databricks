***REMOVED*** ==============================================
***REMOVED*** Core Configuration
***REMOVED*** ==============================================

variable "use_byor_infrastructure" {
  description = <<-EOT
    Use infrastructure from BYOR deployment (network + optional CMK).
    
    When TRUE:  Uses existing resources from deployments/byor
                - Network: VNet, subnets, NSG (required)
                - NAT Gateway: Already created by BYOR (automatic)
                - CMK: Key Vault from BYOR (if CMK enabled)
    
    When FALSE: Creates all resources from scratch
                - Network: New VNet, subnets, NSG
                - NAT Gateway: Created if enable_nat_gateway=true
                - CMK: New Key Vault if create_key_vault=true
  EOT
  type        = bool
  default     = false
}

variable "workspace_prefix" {
  description = "Prefix for resource naming (lowercase alphanumeric, max 12 chars)"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{1,12}$", var.workspace_prefix))
    error_message = "workspace_prefix must be lowercase alphanumeric, max 12 characters"
  }
}

variable "location" {
  description = "Azure region for deployment"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name (will be created if it doesn't exist)"
  type        = string
}

***REMOVED*** ==============================================
***REMOVED*** Databricks Configuration
***REMOVED*** ==============================================

variable "databricks_account_id" {
  description = "Databricks account ID (UUID format, required for Unity Catalog)"
  type        = string

  validation {
    condition     = can(regex("^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", var.databricks_account_id))
    error_message = "databricks_account_id must be a valid UUID"
  }
}

***REMOVED*** ==============================================
***REMOVED*** Network Configuration (BYOV)
***REMOVED*** ==============================================

variable "use_existing_network" {
  description = "Use existing VNet/Subnets/NSG (true) or create new (false). When true, ALL network resources must exist."
  type        = bool
  default     = false
}

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

variable "existing_nsg_name" {
  description = "Name of existing NSG (required if use_existing_network=true)"
  type        = string
  default     = ""
}

variable "existing_public_subnet_nsg_association_id" {
  description = "Resource ID of existing public subnet NSG association (required if use_existing_network=true)"
  type        = string
  default     = ""
}

variable "existing_private_subnet_nsg_association_id" {
  description = "Resource ID of existing private subnet NSG association (required if use_existing_network=true)"
  type        = string
  default     = ""
}

variable "vnet_address_space" {
  description = "Address space for VNet (used when creating new VNet)"
  type        = list(string)
  default     = ["10.100.0.0/16"]
}

variable "public_subnet_address_prefix" {
  description = "Address prefix for public/host subnet (used when creating new subnet)"
  type        = list(string)
  default     = ["10.100.1.0/26"]
}

variable "private_subnet_address_prefix" {
  description = "Address prefix for private/container subnet (used when creating new subnet)"
  type        = list(string)
  default     = ["10.100.2.0/26"]
}

variable "enable_nat_gateway" {
  description = "Create NAT Gateway for stable egress IP (recommended for Non-PL to download packages)"
  type        = bool
  default     = true
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

***REMOVED*** Key Vault Configuration (Create or Bring)
variable "create_key_vault" {
  description = "Create new Key Vault (true) or use existing (false)"
  type        = bool
  default     = true
}

variable "existing_key_vault_id" {
  description = "ID of existing Key Vault (required if create_key_vault=false)"
  type        = string
  default     = ""
}

variable "existing_key_id" {
  description = "ID of existing CMK key in Key Vault (optional, will create if not provided)"
  type        = string
  default     = ""
}

variable "cmk_key_vault_key_id" {
  description = "Azure Key Vault key ID for CMK (auto-populated from Key Vault module or use existing_key_id)"
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
  description = "List of allowed IP ranges in CIDR notation (e.g., ['203.0.113.0/24'])"
  type        = list(string)
  default     = []
}

***REMOVED*** ==============================================
***REMOVED*** Unity Catalog Configuration
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
  description = "Name of the Unity Catalog metastore (auto-generated if empty)"
  type        = string
  default     = ""
}

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
***REMOVED*** Service Endpoint Policy (Optional)
***REMOVED*** ==============================================

variable "enable_service_endpoint_policy" {
  description = "Enable Service Endpoint Policy for storage egress control (classic compute only). Restricts VNet storage access to allow-listed accounts only."
  type        = bool
  default     = false
}

variable "additional_allowed_storage_ids" {
  description = "Additional customer storage account resource IDs to allow in SEP (e.g., existing data lakes, backup storage)"
  type        = list(string)
  default     = []
}

***REMOVED*** ==============================================
***REMOVED*** Tags
***REMOVED*** ==============================================

variable "tag_owner" {
  description = "Owner email address for resource tagging"
  type        = string
  default     = "bhavin.kukadia@databricks.com"
}

variable "tag_keepuntil" {
  description = "Date to keep resources until (format: MM/DD/YYYY)"
  type        = string
  default     = "12/31/2025"
}

variable "tags" {
  description = "Additional tags to apply to all resources (will be merged with owner and keepuntil tags)"
  type        = map(string)
  default = {
    ManagedBy = "Terraform"
    Pattern   = "Non-PL"
  }
}
