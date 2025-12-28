***REMOVED***GCP variables
variable "google_project_name" {
  type = string
}
variable "google_region" {
  type = string
}


variable "external_project" {
  type    = bool
  default = false
}

variable "bucket_project_id" {
  type    = string
  default = ""
}

variable "databricks_google_service_account" {
  type = string
}

variable "metastore_id" {
  type    = string
  default = ""
}

***REMOVED***Databricks account variables
variable "databricks_account_id" {
  description = "Databricks account ID (UUID)"
  type        = string
  sensitive   = true
}

variable "workspace_name" {
  type = string
}

variable "private_access_settings_id" {
  description = "Regional private access settings IDs (map of region to UUID)"
  type        = map(string)
  sensitive   = true
}

variable "dataplane_relay_vpc_endpoint_id" {
  description = "Regional dataplane relay VPC endpoint IDs (ngrok) - map of region to UUID"
  type        = map(string)
  sensitive   = true
}

variable "rest_api_vpc_endpoint_id" {
  description = "Regional REST API VPC endpoint IDs (plproxy) - map of region to UUID"
  type        = map(string)
  sensitive   = true
}

variable "databricks_metastore_id" {
  description = "Regional Unity Catalog metastore IDs - map of region to UUID"
  type        = map(string)
  sensitive   = true
}

variable "permissions_group_role_admin" {
  type    = string
  default = ""
}

variable "permissions_group_role_user" {
  type = string
}

variable "permissions_user_role_admin" {
  type    = string
  default = ""
}

variable "permissions_user_role_user" {
  type    = string
  default = ""
}

variable "permissions_spn_role_admin" {
  type    = string
  default = ""
}

variable "permissions_spn_role_user" {
  type    = string
  default = ""
}

***REMOVED***node
variable "node_type" {
  type    = string
  default = "e2"
}

***REMOVED***Network variables
variable "network_project_id" {
  type = string
}
variable "vpc_id" {
  type = string
}
variable "subnet_id" {
  type = string
}

***REMOVED***Tag Variables
variable "apmid" {
  type = string
}
variable "org" {
  type = string
}

variable "applicationtier" {
  type = string
}

variable "trproductid" {
  type = string
}
variable "ssp" {
  type = string
}
variable "gcpprojectid" {
  type = string
}
variable "costcenter" {
  type = string
}
variable "teamname" {
  type = string
}
variable "owner" {
  type = string
}
variable "environment" {
  type = string
}
variable "notificationdistlist" {
  type = string
}

***REMOVED***cluster variables
***REMOVED***note these have default values can be over-rided when user wants different compute types
variable "small_node_type" {
  type    = string
  default = "e2-standard-4"
}
variable "medium_node_type" {
  type    = string
  default = "e2-standard-8"
}
variable "large_node_type" {
  type    = string
  default = "e2-standard-16"
}
variable "all_node_types" {
  type    = string
  default = "e2-standard-4,e2-standard-8,e2-standard-16,e2-standard-32"
}

variable "compute_types" {
  type = string
}

variable "unity_catalog_config" {
  type    = string
  default = ""
}

variable "ext_unity_catalog_config" {
  type    = string
  default = ""
}

variable "ext_unity_catalog_permissions" {
  type    = string
  default = ""
}

variable "unity_catalog_permissions" {
  type    = string
  default = ""
}

variable "external_location_permissions" {
  type    = string
  default = ""
}

variable "storage_credentials_permissions" {
  type    = string
  default = ""
}


***REMOVED******REMOVED***Databricks SqlWareHouse Variables
variable "sqlwarehouse_cluster_config" {
  type    = string
  default = ""
}

variable "cluster_policy_permissions" {
  type    = string
  default = ""
}

variable "pool_usage_permissions" {
  type    = string
  default = ""
}


variable "foriegn_catalog_bq_connection" {
  type    = string
  default = ""
}



***REMOVED*** MODIFICATION - The following variables are used to control the timing and conditional creation of Databricks workspace resources.
***REMOVED*** "expected_workspace_status" allows for checks on workspace state; "provision_workspace_resources" should only be set to true once the workspace is RUNNING.
***REMOVED*** This prevents race conditions and ensures resources are provisioned only when appropriate.

variable "expected_workspace_status" {
  type    = string
  default = "PROVISIONING"
}

variable "provision_workspace_resources" {
  type        = bool
  default     = false
  description = "Set to true to create workspace resources (computes, catalogs, permissions, etc). Only use after workspace is RUNNING."
}

***REMOVED*** MODIFICATION
***REMOVED*** COMMENTED OUT: Variables for Google Workspace Group membership (requires additional permissions)
***REMOVED*** REQUIRED PERMISSION: ccc.hosted.frontend.directory.v1.DirectoryMembers.Insert
***REMOVED*** TO ENABLE: Uncomment after configuring domain-wide delegation and admin user impersonation
***REMOVED*** variable "workspace_operator_group_email" {
***REMOVED***   type        = string
***REMOVED***   default     = ""
***REMOVED***   description = "Google Workspace Group email to add workspace GSA as member. Leave empty to skip group membership."
***REMOVED*** }
***REMOVED*** 
***REMOVED*** variable "google_workspace_customer_id" {
***REMOVED***   type        = string
***REMOVED***   default     = ""
***REMOVED***   description = "Google Workspace customer ID (format: C***REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED***). Required if workspace_operator_group_email is set. Get via: gcloud organizations list"
***REMOVED*** }
