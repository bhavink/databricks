# CIDR block for the VNet's spoke subnet, defining IP range for the network.
variable "spokecidr" {
  type    = string
  default = "10.178.0.0/20"
}

# Boolean flag to determine if public IPs should be disabled.
# Default is true, meaning no public IPs will be assigned.
variable "no_public_ip" {
  type    = bool
  default = true
}

# Azure region where the resource group and resources will be deployed.
variable "rglocation" {
  type    = string
  default = "westus"
}

# Prefix for DBFS (Databricks File System) storage accounts, used to identify DBFS resources.
variable "dbfs_prefix" {
  type    = string
  default = "dbfs"
}

# Prefix used in naming the Databricks workspace, helping to uniquely identify it.
variable "workspace_prefix" {
  type    = string
  default = "dbwbk"
}

# Email of the admin user for the Databricks workspace, with access rights and administrative privileges.
variable "admin_user" {
  type    = string
  default = "bhavin.kukadia@databricks.com"
}

# Name of the Unity Catalog root storage account, required for managing Unity Catalog metadata.
variable "uc_root_storage" {
  type    = string
  default = "ucrootstorage"
}

# Name of the Unity Catalog external storage account, used for storing external datasets.
variable "uc_ext_storage" {
  type    = string
  default = "ucextstorage1"
}

# Environment designation for the deployment, e.g., Development, Testing, Production.
variable "environment" {
  type    = string
  default = "Testing"
}

# Tag to specify the environment for resource management and identification.
variable "tags_environment" {
  type    = string
  default = "Testing"
}

# Tag indicating the owner of the resources, helpful for administrative and support purposes.
variable "tags_owner" {
  type    = string
  default = "bhavin.kukadia@databricks.com"
}

# Epoch tag, typically used for versioning or specifying a unique deployment identifier.
variable "tags_epoch" {
  type    = string
  default = ""
}

# Date indicating when the resources should be removed or reviewed for deletion, supporting lifecycle management.
variable "tags_removeafter" {
  type    = string
  default = "2025-12-31"
}
