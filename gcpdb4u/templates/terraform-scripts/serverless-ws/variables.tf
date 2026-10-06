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
  description = "Name of the new serverless workspace"
}

variable "google_region" {
  type        = string
  description = "Region of the workspace, e.g. us-east4"
}
