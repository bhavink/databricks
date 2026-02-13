# ==============================================
# Standalone Non-PL — Variables
# ==============================================

variable "location" {
  description = "Azure region (e.g. East US)"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "workspace_prefix" {
  description = "Prefix for workspace and network resources (e.g. adb-nonpl)"
  type        = string
}

variable "vnet_address_space" {
  description = "VNet address space"
  type        = list(string)
  default     = ["10.139.0.0/16"]
}

variable "public_subnet_address_prefix" {
  description = "Public subnet CIDR"
  type        = list(string)
  default     = ["10.139.0.0/24"]
}

variable "private_subnet_address_prefix" {
  description = "Private subnet CIDR"
  type        = list(string)
  default     = ["10.139.1.0/24"]
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

# ----------------------------------------------
# Existing Unity Catalog (optional)
# ----------------------------------------------
variable "existing_metastore_id" {
  description = "Existing Unity Catalog metastore ID (UUID). When set, workspace is attached to this metastore. Leave empty to skip UC attachment."
  type        = string
  default     = ""
}

variable "databricks_host" {
  description = "Databricks workspace URL for the provider (e.g. https://adb-xxxx.azuredatabricks.net). Set after first apply when using existing_metastore_id."
  type        = string
  default     = ""
  sensitive   = true
}

variable "default_catalog_name" {
  description = "Default catalog name for the metastore assignment (when using existing_metastore_id)"
  type        = string
  default     = "hive_metastore"
}
