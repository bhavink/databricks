***REMOVED*** ============================================================================
***REMOVED*** Required Variables
***REMOVED*** ============================================================================

variable "prefix" {
  description = "Prefix for resource naming (with random suffix)"
  type        = string
}

variable "suffix" {
  description = "Random suffix for resource naming"
  type        = string
}

variable "databricks_account_id" {
  description = "Databricks account ID"
  type        = string
}

variable "root_storage_bucket_name" {
  description = "Base name for root storage bucket"
  type        = string
}

variable "unity_catalog_bucket_name" {
  description = "Base name for Unity Catalog metastore bucket"
  type        = string
}

variable "unity_catalog_external_bucket_name" {
  description = "Base name for Unity Catalog external location bucket"
  type        = string
}

variable "unity_catalog_root_storage_bucket_name" {
  description = "Base name for Unity Catalog root storage bucket"
  type        = string
}

variable "enable_encryption" {
  description = "Enable KMS encryption for S3 buckets"
  type        = bool
  default     = false
}

variable "kms_key_arn" {
  description = "KMS key ARN for S3 bucket encryption (if enabled)"
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

***REMOVED*** ============================================================================
***REMOVED*** Conditional Resource Creation
***REMOVED*** ============================================================================

variable "create_uc_root_storage_bucket" {
  description = "Whether to create the Unity Catalog root storage bucket. Set to false when using an existing metastore."
  type        = bool
  default     = true
}

