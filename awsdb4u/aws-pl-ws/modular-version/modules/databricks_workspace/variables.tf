variable "prefix" {
  description = "Prefix for resource naming"
  type        = string
}

variable "workspace_name" {
  description = "Name of the Databricks workspace"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
}

variable "databricks_account_id" {
  description = "Databricks account ID"
  type        = string
}

variable "workspace_admin_email" {
  description = "Email of workspace admin user"
  type        = string
}

variable "client_id" {
  description = "Databricks service principal client ID"
  type        = string
}

variable "client_secret" {
  description = "Databricks service principal client secret"
  type        = string
  sensitive   = true
}

variable "vpc_id" {
  description = "VPC ID for workspace"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs"
  type        = list(string)
}

variable "workspace_security_group_id" {
  description = "Security group ID for workspace"
  type        = string
}

variable "workspace_vpce_id" {
  description = "Workspace VPC endpoint ID"
  type        = string
}

variable "relay_vpce_id" {
  description = "Relay VPC endpoint ID"
  type        = string
}

variable "root_storage_bucket" {
  description = "Root storage bucket name"
  type        = string
}

variable "cross_account_role_arn" {
  description = "Cross-account IAM role ARN"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# ============================================================================
# Private Access Settings
# ============================================================================

variable "public_access_enabled" {
  description = "Allow public access to the workspace (set to false for fully private workspace)"
  type        = bool
  default     = true
}

variable "private_access_level" {
  description = "Private access level (ACCOUNT or ENDPOINT)"
  type        = string
  default     = "ENDPOINT"

  validation {
    condition     = contains(["ACCOUNT", "ENDPOINT"], var.private_access_level)
    error_message = "private_access_level must be either 'ACCOUNT' or 'ENDPOINT'."
  }
}

# ============================================================================
# IP Access Lists (Optional)
# ============================================================================

variable "enable_ip_access_lists" {
  description = "Enable IP access lists for workspace security"
  type        = bool
  default     = false
}

variable "allowed_ip_addresses" {
  description = "List of allowed IP addresses/CIDR ranges for workspace access"
  type        = list(string)
  default     = []
}

# ============================================================================
# Workspace CMK (Optional)
# ============================================================================

variable "enable_workspace_cmk" {
  description = "Enable Customer Managed Keys for workspace encryption (both storage and managed services)"
  type        = bool
  default     = false
}

variable "workspace_storage_key_arn" {
  description = "KMS key ARN for workspace encryption (DBFS, EBS, and managed services)"
  type        = string
  default     = ""
}

variable "workspace_storage_key_alias" {
  description = "KMS key alias for workspace encryption"
  type        = string
  default     = ""
}

