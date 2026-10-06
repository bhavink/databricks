variable "databricks_account_id" {
  type        = string
  description = "Databricks account ID. Set with TF_VAR_databricks_account_id; never commit it."
}

variable "databricks_account_console_url" {
  type        = string
  description = "Account console URL"
  default     = "https://accounts.cloud.databricks.com"
}

variable "workspace_name" {
  type        = string
  description = "Name of the new serverless workspace"
}

variable "region" {
  type        = string
  description = "AWS region of the workspace, e.g. us-west-2 (serverless workspaces are not available in GovCloud)"

  validation {
    condition     = !startswith(var.region, "us-gov-")
    error_message = "Serverless workspaces are not available in GovCloud regions."
  }
}
