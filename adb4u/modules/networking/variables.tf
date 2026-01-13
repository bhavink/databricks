***REMOVED*** ==============================================
***REMOVED*** Bring Your Own VNet (BYOV) Configuration
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

***REMOVED*** ==============================================
***REMOVED*** New Network Configuration
***REMOVED*** ==============================================

variable "vnet_address_space" {
  description = "Address space for VNet (CIDR /16 to /24). Used when creating new VNet."
  type        = list(string)
  default     = ["10.0.0.0/16"]

  validation {
    condition     = can([for cidr in var.vnet_address_space : cidrhost(cidr, 0)])
    error_message = "Must be valid CIDR notation"
  }
}

variable "public_subnet_address_prefix" {
  description = "Address prefix for public/host subnet (CIDR at least /26). Used when creating new subnet."
  type        = list(string)
  default     = ["10.0.1.0/26"]

  validation {
    condition     = can([for cidr in var.public_subnet_address_prefix : cidrhost(cidr, 0)])
    error_message = "Must be valid CIDR notation"
  }
}

variable "private_subnet_address_prefix" {
  description = "Address prefix for private/container subnet (CIDR at least /26). Used when creating new subnet."
  type        = list(string)
  default     = ["10.0.2.0/26"]

  validation {
    condition     = can([for cidr in var.private_subnet_address_prefix : cidrhost(cidr, 0)])
    error_message = "Must be valid CIDR notation"
  }
}

***REMOVED*** ==============================================
***REMOVED*** Private Link Configuration
***REMOVED*** ==============================================

variable "enable_private_link" {
  description = "Enable Private Link for front-end (UI/API) and back-end (data plane). When true, workspace is fully private (no public access)."
  type        = bool
  default     = false
}

variable "enable_public_network_access" {
  description = "Whether public network access is enabled on the workspace. Custom NSG rules are only created when Private Link is enabled AND public access is disabled."
  type        = bool
  default     = true
}

variable "privatelink_subnet_address_prefix" {
  description = "Address prefix for Private Link subnet (CIDR at least /27). Required when enable_private_link=true for hosting private endpoints."
  type        = list(string)
  default     = ["10.0.3.0/27"]

  validation {
    condition     = can([for cidr in var.privatelink_subnet_address_prefix : cidrhost(cidr, 0)])
    error_message = "Must be valid CIDR notation"
  }
}

variable "existing_privatelink_subnet_name" {
  description = "Name of existing Private Link subnet (optional if use_existing_network=true and enable_private_link=true)"
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

***REMOVED*** ==============================================
***REMOVED*** Service Endpoint Policy Configuration
***REMOVED*** ==============================================

variable "service_endpoint_policy_ids" {
  description = "List of Service Endpoint Policy IDs to associate with Databricks subnets (for storage egress control)"
  type        = list(string)
  default     = []
}

***REMOVED*** ==============================================
***REMOVED*** NAT Gateway Configuration
***REMOVED*** ==============================================

variable "enable_nat_gateway" {
  description = "Create NAT Gateway for stable egress IP. Recommended for Non-PL pattern to download packages (PyPI, Maven, etc.). Mutually exclusive with enable_private_link (air-gapped)."
  type        = bool
  default     = true
}

***REMOVED*** ==============================================
***REMOVED*** Required Configuration
***REMOVED*** ==============================================

variable "location" {
  description = "Azure region for network resources"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name for network resources"
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
  description = "Tags to apply to all network resources"
  type        = map(string)
  default     = {}
}
