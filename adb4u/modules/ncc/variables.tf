# ==============================================
# Required Configuration
# ==============================================

variable "location" {
  description = "Azure region for Network Connectivity Configuration"
  type        = string
}

variable "workspace_prefix" {
  description = "Prefix for resource naming (lowercase alphanumeric, max 12 chars)"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{1,12}$", var.workspace_prefix))
    error_message = "workspace_prefix must be lowercase alphanumeric, max 12 characters"
  }
}

# ==============================================
# Workspace Configuration
# ==============================================

variable "workspace_id_numeric" {
  description = "Numeric Databricks workspace ID (not Azure resource ID)"
  type        = string
}

# ==============================================
# Serverless Egress Control (Optional)
# ==============================================
# Serverless compute does not traverse your VNet firewall. A network policy
# in RESTRICTED_ACCESS mode limits serverless egress to allowed destinations.
# See: https://learn.microsoft.com/en-us/azure/databricks/security/network/serverless-network-security/network-policies

variable "enable_network_policy" {
  description = "Create a serverless network policy and assign it to the workspace"
  type        = bool
  default     = false
}

variable "network_policy_enforcement_mode" {
  description = "ENFORCED blocks disallowed egress; DRY_RUN only logs denials (use to stage a rollout)"
  type        = string
  default     = "ENFORCED"

  validation {
    condition     = contains(["ENFORCED", "DRY_RUN"], var.network_policy_enforcement_mode)
    error_message = "network_policy_enforcement_mode must be ENFORCED or DRY_RUN"
  }
}

variable "allowed_internet_destinations" {
  description = "FQDNs serverless compute may reach (e.g. [\"pypi.org\", \"files.pythonhosted.org\"])"
  type        = list(string)
  default     = []
}

variable "allowed_storage_accounts" {
  description = "Azure storage account names serverless compute may reach, in addition to Unity Catalog locations"
  type        = list(string)
  default     = []
}
