variable "databricks_account_id" {
  type        = string
  description = "Databricks account ID. Set with TF_VAR_databricks_account_id; never commit it."
}

variable "databricks_account_console_url" {
  type        = string
  description = "Account console URL"
  default     = "https://accounts.gcp.databricks.com"
}

variable "google_service_account_email" {
  type        = string
  description = "Service account Terraform impersonates (an account admin), as in the other gcpdb4u roots"
}

variable "databricks_workspace_name" {
  type        = string
  description = "Name of the existing workspace to secure (same value as in the workspace deployment)"
}

variable "workspace_url" {
  type        = string
  description = "URL of the workspace, e.g. the workspace_url output of the workspace deployment"

  validation {
    condition     = can(regex("^https://", var.workspace_url))
    error_message = "workspace_url must start with https://."
  }
}

variable "google_region" {
  type        = string
  description = "Workspace region (for the network connectivity config)"
}

# ----------------------------------------------------------------- inbound

variable "enable_ip_access_list" {
  type        = bool
  description = "Restrict the workspace front-end to the ranges in ip_access_list.yaml. Include your own egress IP."
  default     = true
}

# ----------------------------------------------------------------- serverless egress

variable "enable_ncc" {
  type        = bool
  description = "Create a network connectivity config and bind it to the workspace"
  default     = true
}

variable "enable_network_policy" {
  type        = bool
  description = "Restrict serverless egress to network_policy.yaml (RESTRICTED_ACCESS)"
  default     = true
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

variable "shared_network_policy_id" {
  type        = string
  description = "Bind an existing shared network policy instead of creating one for this workspace"
  default     = ""
}
