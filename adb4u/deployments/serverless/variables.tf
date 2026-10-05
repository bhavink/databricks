# ==============================================
# Core
# ==============================================

variable "workspace_prefix" {
  type        = string
  description = "Prefix for resource names (lowercase alphanumeric, max 12 characters)"

  validation {
    condition     = can(regex("^[a-z0-9]{1,12}$", var.workspace_prefix))
    error_message = "workspace_prefix must be 1-12 lowercase letters or digits."
  }
}

variable "location" {
  type        = string
  description = "Azure region, e.g. eastus2. Must support serverless workspaces (Default Storage)."
}

variable "resource_group_name" {
  type        = string
  description = "Resource group to create for the workspace and its network"
}

variable "databricks_account_id" {
  type        = string
  description = "Databricks account ID. Set with TF_VAR_databricks_account_id; never commit it."
}

variable "metastore_id" {
  type        = string
  description = "ID of the existing Unity Catalog metastore in this region (one metastore per region)"
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to all resources"
  default     = {}
}

# ==============================================
# Network (private endpoint subnet only)
# ==============================================
# Serverless compute runs in Databricks' account, not in this VNet. The VNet
# holds the private endpoints: browser authentication (always created by the
# official module) and the front-end endpoint when public access is disabled.

variable "vnet_address_space" {
  type        = list(string)
  description = "Address space of the private endpoint VNet"
  default     = ["10.180.0.0/24"]
}

variable "privatelink_subnet_address_prefix" {
  type        = list(string)
  description = "Address prefix of the private endpoint subnet"
  default     = ["10.180.0.0/27"]
}

# ==============================================
# Front-end access
# ==============================================

variable "enable_public_network_access" {
  type        = bool
  description = "Allow access to the workspace from the internet. When false, users connect through the front-end private endpoint."
  default     = true
}

variable "enable_ip_access_lists" {
  type        = bool
  description = "Restrict the public front-end to allowed_ip_ranges"
  default     = false
}

variable "allowed_ip_ranges" {
  type        = list(string)
  description = "CIDR ranges allowed to reach the workspace when IP access lists are enabled"
  default     = []
}

variable "additional_workspace_config" {
  type        = map(string)
  description = "Extra workspace settings, e.g. { enableExportNotebook = \"false\" }"
  default     = {}
}

# ==============================================
# Encryption
# ==============================================

variable "managed_services_cmk_key_id" {
  type        = string
  description = "Key Vault key URI (https://<vault>.vault.azure.net/keys/<name>/<version>) for managed services CMK. Null disables CMK."
  default     = null
}

# ==============================================
# Serverless egress
# ==============================================

variable "enable_network_policy" {
  type        = bool
  description = "Restrict serverless egress (RESTRICTED_ACCESS). When false, the policy allows full access."
  default     = false
}

variable "network_policy_enforcement_mode" {
  type        = string
  description = "ENFORCED blocks traffic; DRY_RUN only logs denials"
  default     = "ENFORCED"

  validation {
    condition     = contains(["ENFORCED", "DRY_RUN"], var.network_policy_enforcement_mode)
    error_message = "network_policy_enforcement_mode must be ENFORCED or DRY_RUN."
  }
}

variable "serverless_allowed_internet_destinations" {
  type        = list(string)
  description = "FQDNs serverless compute may reach when the network policy is restricted"
  default     = []
}

variable "serverless_allowed_storage_accounts" {
  type        = list(string)
  description = "Storage account names serverless compute may reach (dfs) when the network policy is restricted"
  default     = []
}

# ==============================================
# Diagnostic logs
# ==============================================

variable "enable_diagnostic_settings" {
  type        = bool
  description = "Export workspace diagnostic (audit) logs"
  default     = false
}

variable "diagnostic_log_analytics_workspace_id" {
  type        = string
  description = "Log Analytics workspace resource ID for diagnostic logs"
  default     = ""
}

variable "diagnostic_storage_account_id" {
  type        = string
  description = "Storage account resource ID for diagnostic logs"
  default     = ""
}

variable "diagnostic_eventhub_authorization_rule_id" {
  type        = string
  description = "Event Hub authorization rule ID for diagnostic logs"
  default     = ""
}

variable "diagnostic_eventhub_name" {
  type        = string
  description = "Event Hub name for diagnostic logs"
  default     = ""
}

variable "serverless_private_endpoint_storage_account_ids" {
  type        = list(string)
  description = "Storage account resource IDs serverless compute reaches over private endpoints (dfs). Each endpoint must be approved on the storage account."
  default     = []
}
