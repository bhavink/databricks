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
  description = "Databricks service principal client ID (for provider authentication)"
  type        = string
}

variable "client_secret" {
  description = "Databricks service principal client secret (for provider authentication)"
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

***REMOVED*** ============================================================================
***REMOVED*** VPC Endpoint Configuration
***REMOVED*** ============================================================================

variable "enable_private_link" {
  description = "Whether Databricks Private Link is enabled (creates both workspace and relay VPC endpoints)"
  type        = bool
  default     = true
}

variable "workspace_vpce_id" {
  description = "Workspace VPC endpoint ID (used for both frontend and backend Private Link scenarios)"
  type        = string
  default     = null
}

variable "relay_vpce_id" {
  description = "Relay VPC endpoint ID (used for backend Private Link - Secure Cluster Connectivity)"
  type        = string
  default     = null
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

***REMOVED*** ============================================================================
***REMOVED*** Private Access Settings
***REMOVED*** NOTE: PAS is an ACCOUNT-LEVEL object that can be SHARED across multiple workspaces
***REMOVED*** Typically used when multiple workspaces share a transit VPC for frontend Private Link
***REMOVED*** ============================================================================

variable "existing_private_access_settings_id" {
  description = <<-EOT
    OPTIONAL: Existing Private Access Settings ID to reuse across multiple workspaces.

    Architecture Note:
    - PAS is an ACCOUNT-LEVEL object that can be attached to MULTIPLE workspaces
    - Controls FRONTEND Private Link behavior (public_access_enabled)
    - Typically shared when multiple workspaces use the same transit VPC

    When to provide this:
    - Multi-workspace deployments sharing frontend Private Link configuration
    - Second, third, etc. workspaces in the same transit VPC setup

    When to leave empty:
    - First workspace deployment (module will create new PAS)
    - Workspace needs different frontend access settings than other workspaces

    If provided, module will skip PAS creation and use existing PAS.
    Network Configuration is always created (one per workspace, not reusable).
  EOT
  type        = string
  default     = ""
}

variable "public_access_enabled" {
  description = <<-EOT
    Controls public internet access to workspace UI/API when Private Link is enabled.

    Use Cases:
    - enable_private_link=true + public_access_enabled=false:
      Maximum security - All access via Private Link only, no public internet access
    - enable_private_link=true + public_access_enabled=true:
      Hybrid access - Private Link available but public access also allowed (with optional IP ACLs)
    - enable_private_link=false:
      This setting is ignored - workspace is publicly accessible via NAT gateway

    Default: true (allows public access alongside Private Link for flexibility)
  EOT
  type        = bool
  default     = true
}

variable "private_access_level" {
  description = "Private access level for backend communication. ACCOUNT = public relay (default), ENDPOINT = uses backend VPC endpoint. Set to ENDPOINT only when backend VPC endpoint is enabled and tested."
  type        = string
  default     = "ACCOUNT"

  validation {
    condition     = contains(["ACCOUNT", "ENDPOINT"], var.private_access_level)
    error_message = "private_access_level must be either 'ACCOUNT' or 'ENDPOINT'."
  }
}

***REMOVED*** ============================================================================
***REMOVED*** IP Access Lists (Optional)
***REMOVED*** ============================================================================

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

***REMOVED*** ============================================================================
***REMOVED*** Workspace CMK (Optional)
***REMOVED*** ============================================================================

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

