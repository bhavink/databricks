# ============================================================================
# Required Variables
# ============================================================================

variable "prefix" {
  description = "Prefix for resource naming (with random suffix)"
  type        = string
}

variable "region" {
  description = "AWS region for deployment"
  type        = string
}

variable "workspace_name" {
  description = "Name of the Databricks workspace"
  type        = string
}

variable "workspace_id" {
  description = "Databricks workspace ID"
  type        = string
}

variable "workspace_admin_email" {
  description = "Email address of existing workspace administrator (from account console) to assign as workspace admin via UC. Leave empty to skip."
  type        = string
  default     = ""
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

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
}

variable "databricks_account_id" {
  description = "Databricks account ID"
  type        = string
}

variable "create_workspace_catalog" {
  description = "Whether to create workspace catalog with external location (set to false to skip for clean destroy)"
  type        = bool
  default     = true
}

# ============================================================================
# S3 Bucket Names
# ============================================================================

variable "unity_catalog_root_storage_bucket" {
  description = "S3 bucket name for Unity Catalog root storage"
  type        = string
}

variable "unity_catalog_external_bucket" {
  description = "S3 bucket name for Unity Catalog external location"
  type        = string
}

# ============================================================================
# Tags
# ============================================================================

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

