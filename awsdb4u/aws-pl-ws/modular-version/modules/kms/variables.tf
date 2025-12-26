***REMOVED*** ============================================================================
***REMOVED*** Required Variables
***REMOVED*** ============================================================================

variable "prefix" {
  description = "Prefix for resource naming (with random suffix)"
  type        = string
}

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
}

variable "databricks_account_id" {
  description = "Databricks account ID (for KMS key policy)"
  type        = string
}

variable "enable_encryption" {
  description = "Enable KMS encryption for S3 buckets"
  type        = bool
  default     = false
}

variable "kms_key_deletion_window" {
  description = "KMS key deletion window in days"
  type        = number
  default     = 30
}

***REMOVED*** ============================================================================
***REMOVED*** Workspace CMK Variables
***REMOVED*** ============================================================================

variable "enable_workspace_cmk" {
  description = "Enable Customer Managed Keys for workspace storage and managed services encryption"
  type        = bool
  default     = false
}

variable "cmk_admin_arn" {
  description = "ARN of the IAM user/role that will administer the CMK (defaults to account root)"
  type        = string
  default     = null
}

***REMOVED*** ============================================================================
***REMOVED*** Tags
***REMOVED*** ============================================================================

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

