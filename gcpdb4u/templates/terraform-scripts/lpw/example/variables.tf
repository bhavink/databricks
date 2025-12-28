***REMOVED*** MODIFICATION: Single phase variable for simplified deployment
***REMOVED*** Reason: Avoid editing main.tf between phases, pass -var="phase=X" instead
variable "phase" {
  type        = string
  description = "Deployment phase: PROVISIONING or RUNNING (case-insensitive)"
  default     = "PROVISIONING"

  validation {
    condition     = contains(["PROVISIONING", "RUNNING"], upper(var.phase))
    error_message = "Phase must be PROVISIONING or RUNNING (case-insensitive)."
  }
}

***REMOVED*** ========================================================================
***REMOVED*** Databricks Account Configuration
***REMOVED*** ========================================================================

variable "databricks_account_id" {
  description = "Databricks account ID (UUID)"
  type        = string
  sensitive   = true
}

variable "databricks_google_service_account" {
  description = "GCP service account email for Databricks workspace authentication"
  type        = string
}

***REMOVED*** ========================================================================
***REMOVED*** Regional Databricks Configuration
***REMOVED*** ========================================================================

variable "private_access_settings_id" {
  description = "Regional private access settings IDs (map of region to UUID)"
  type        = map(string)
  sensitive   = true
}

variable "dataplane_relay_vpc_endpoint_id" {
  description = "Regional dataplane relay VPC endpoint IDs / ngrok (map of region to UUID)"
  type        = map(string)
  sensitive   = true
}

variable "rest_api_vpc_endpoint_id" {
  description = "Regional REST API VPC endpoint IDs / plproxy (map of region to UUID)"
  type        = map(string)
  sensitive   = true
}

variable "databricks_metastore_id" {
  description = "Regional Unity Catalog metastore IDs (map of region to UUID)"
  type        = map(string)
  sensitive   = true
}

***REMOVED*** ========================================================================
***REMOVED*** Workspace Configuration
***REMOVED*** ========================================================================

variable "workspace_name" {
  description = "Name of the Databricks workspace"
  type        = string
}

variable "metastore_id" {
  description = "Unity Catalog metastore ID to assign to this workspace"
  type        = string
}

***REMOVED*** ========================================================================
***REMOVED*** GCP Network Configuration
***REMOVED*** ========================================================================

variable "network_project_id" {
  description = "GCP project ID containing the VPC network"
  type        = string
}

variable "vpc_id" {
  description = "VPC network name"
  type        = string
}

variable "subnet_id" {
  description = "Subnet name for Databricks nodes"
  type        = string
}

***REMOVED*** ========================================================================
***REMOVED*** GCP Project Configuration
***REMOVED*** ========================================================================

variable "gcpprojectid" {
  description = "GCP project ID for Databricks workspace resources"
  type        = string
}

variable "google_project_name" {
  description = "GCP project name for Databricks workspace resources"
  type        = string
}

variable "google_region" {
  description = "GCP region for Databricks workspace"
  type        = string
  default     = "us-east4"
}

***REMOVED*** ========================================================================
***REMOVED*** Metadata and Tags
***REMOVED*** ========================================================================

variable "notificationdistlist" {
  description = "Email distribution list for notifications"
  type        = string
}

variable "teamname" {
  description = "Team name for tagging"
  type        = string
}

variable "org" {
  description = "Organization name for tagging"
  type        = string
}

variable "owner" {
  description = "Owner email address for tagging"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "applicationtier" {
  description = "Application tier for tagging"
  type        = string
  default     = "tier2"
}

***REMOVED*** ========================================================================
***REMOVED*** Optional: Billing and Tracking Codes
***REMOVED*** ========================================================================

variable "costcenter" {
  description = "Cost center code for billing tracking (optional)"
  type        = string
  default     = ""
}

variable "apmid" {
  description = "APM ID for billing tracking (optional)"
  type        = string
  default     = ""
}

variable "ssp" {
  description = "SSP code for billing tracking (optional)"
  type        = string
  default     = ""
}

variable "trproductid" {
  description = "Product ID for billing tracking (optional)"
  type        = string
  default     = ""
}

***REMOVED*** ========================================================================
***REMOVED*** Compute Configuration
***REMOVED*** ========================================================================

variable "node_type" {
  description = "GCP machine type family (e2, n1, n2, etc.)"
  type        = string
  default     = "e2"
}

variable "compute_types" {
  description = "Comma-separated list of compute pool sizes to create (Small, Medium, Large)"
  type        = string
  default     = "Small,Medium,Large"
}

***REMOVED*** ========================================================================
***REMOVED*** Permissions Configuration
***REMOVED*** ========================================================================

variable "permissions_group_role_user" {
  description = "Comma-separated list of groups to grant USER role"
  type        = string
}

variable "permissions_group_role_admin" {
  description = "Comma-separated list of groups to grant ADMIN role"
  type        = string
  default     = ""
}

variable "permissions_user_role_user" {
  description = "Comma-separated list of users to grant USER role"
  type        = string
  default     = ""
}

variable "permissions_spn_role_user" {
  description = "Comma-separated list of service principals to grant USER role"
  type        = string
  default     = ""
}

variable "permissions_spn_role_admin" {
  description = "Comma-separated list of service principals to grant ADMIN role"
  type        = string
  default     = ""
}

variable "cluster_policy_permissions" {
  description = "JSON string defining cluster policy permissions"
  type        = string
}

variable "pool_usage_permissions" {
  description = "JSON string defining instance pool usage permissions"
  type        = string
}

***REMOVED*** ========================================================================
***REMOVED*** External Project Configuration
***REMOVED*** ========================================================================

variable "external_project" {
  description = "Whether to use external project for GCS buckets"
  type        = bool
  default     = false
}

variable "bucket_project_id" {
  description = "GCP project ID for external buckets (if external_project = true)"
  type        = string
  default     = ""
}

***REMOVED*** ========================================================================
***REMOVED*** Unity Catalog Configuration
***REMOVED*** ========================================================================

variable "unity_catalog_config" {
  description = "JSON string defining Unity Catalog configuration"
  type        = string
}

variable "unity_catalog_permissions" {
  description = "JSON string defining Unity Catalog permissions"
  type        = string
}

variable "external_location_permissions" {
  description = "JSON string defining external location permissions"
  type        = string
}

variable "storage_credentials_permissions" {
  description = "JSON string defining storage credentials permissions"
  type        = string
}

***REMOVED*** ========================================================================
***REMOVED*** SQL Warehouse Configuration
***REMOVED*** ========================================================================

variable "sqlwarehouse_cluster_config" {
  description = "JSON string defining SQL warehouse configuration"
  type        = string
}

