***REMOVED*** ==============================================
***REMOVED*** Core Configuration
***REMOVED*** ==============================================

variable "workspace_prefix" {
  description = "Prefix for all resources (lowercase, alphanumeric only, max 12 chars)"
  type        = string
  
  validation {
    condition     = can(regex("^[a-z0-9]{1,12}$", var.workspace_prefix))
    error_message = "workspace_prefix must be lowercase alphanumeric only, max 12 characters"
  }
}

variable "location" {
  description = "Azure region for resources (e.g., 'eastus2', 'westus2')"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group to create or use"
  type        = string
}

variable "use_existing_resource_group" {
  description = "Use an existing resource group instead of creating a new one"
  type        = bool
  default     = false
}

***REMOVED*** ==============================================
***REMOVED*** Network Configuration
***REMOVED*** ==============================================

variable "vnet_address_space" {
  description = "Address space for the VNet (e.g., ['10.100.0.0/16'])"
  type        = list(string)
}

variable "public_subnet_address_prefix" {
  description = "Address prefix for public/host subnet (minimum /26, e.g., '10.100.1.0/26')"
  type        = string
  
  validation {
    condition     = can(cidrnetmask(var.public_subnet_address_prefix))
    error_message = "public_subnet_address_prefix must be a valid CIDR block"
  }
}

variable "private_subnet_address_prefix" {
  description = "Address prefix for private/container subnet (minimum /26, e.g., '10.100.2.0/26')"
  type        = string
  
  validation {
    condition     = can(cidrnetmask(var.private_subnet_address_prefix))
    error_message = "private_subnet_address_prefix must be a valid CIDR block"
  }
}

variable "create_privatelink_subnet" {
  description = "Create a Private Link subnet for Full-Private pattern (optional)"
  type        = bool
  default     = false
}

variable "privatelink_subnet_address_prefix" {
  description = "Address prefix for Private Link subnet (minimum /26, e.g., '10.100.3.0/26'). Required if create_privatelink_subnet=true"
  type        = string
  default     = ""
}

variable "enable_nat_gateway" {
  description = "Create NAT Gateway for internet egress (required for Non-PL pattern, not needed for Full-Private)"
  type        = bool
  default     = false
}

***REMOVED*** ==============================================
***REMOVED*** Customer-Managed Keys (Optional)
***REMOVED*** ==============================================

variable "create_key_vault" {
  description = "Create Key Vault and CMK key for Databricks encryption (optional)"
  type        = bool
  default     = false
}

variable "cmk_key_type" {
  description = "Type of CMK key (RSA, RSA-HSM)"
  type        = string
  default     = "RSA"
  
  validation {
    condition     = contains(["RSA", "RSA-HSM"], var.cmk_key_type)
    error_message = "cmk_key_type must be either 'RSA' or 'RSA-HSM'"
  }
}

variable "cmk_key_size" {
  description = "Size of CMK key in bits (2048, 3072, 4096)"
  type        = number
  default     = 2048
  
  validation {
    condition     = contains([2048, 3072, 4096], var.cmk_key_size)
    error_message = "cmk_key_size must be 2048, 3072, or 4096"
  }
}

***REMOVED*** ==============================================
***REMOVED*** Resource Tagging
***REMOVED*** ==============================================

variable "tag_owner" {
  description = "Mandatory tag: Owner of the resource (e.g., team email)"
  type        = string
}

variable "tag_keepuntil" {
  description = "Mandatory tag: Date until which the resource should be kept (e.g., 'MM/DD/YYYY')"
  type        = string
}

variable "tags" {
  description = "Additional custom tags to apply to all resources (will be merged with owner and keepuntil tags)"
  type        = map(string)
  default = {
    Environment = "Production"
    ManagedBy   = "Terraform"
    Pattern     = "BYOR"
  }
}
