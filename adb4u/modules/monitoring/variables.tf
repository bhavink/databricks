# ==============================================
# Monitoring Module Variables
# ==============================================

variable "workspace_id" {
  description = "Azure resource ID of the Databricks workspace to export diagnostic logs from"
  type        = string
}

variable "diagnostic_setting_name" {
  description = "Name of the diagnostic setting"
  type        = string
  default     = "databricks-diagnostics"
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace resource ID (destination). At least one destination is required."
  type        = string
  default     = ""
}

variable "storage_account_id" {
  description = "Storage account resource ID for log archival (destination)"
  type        = string
  default     = ""
}

variable "eventhub_authorization_rule_id" {
  description = "Event Hub namespace authorization rule ID for SIEM streaming (destination)"
  type        = string
  default     = ""
}

variable "eventhub_name" {
  description = "Event Hub name (optional; namespace default hub is used when empty)"
  type        = string
  default     = ""
}
