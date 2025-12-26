# ============================================================================
# Required Variables
# ============================================================================

variable "prefix" {
  description = "Prefix for resource naming (with random suffix)"
  type        = string
}

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
}

variable "databricks_account_id" {
  description = "Databricks account ID"
  type        = string
}

variable "unity_catalog_bucket_arn" {
  description = "ARN of Unity Catalog metastore bucket"
  type        = string
}

variable "unity_catalog_external_bucket_arn" {
  description = "ARN of Unity Catalog external location bucket"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

