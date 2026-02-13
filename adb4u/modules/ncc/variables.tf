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
