# ============================================================================
# User Assignment Module - Variables
# ============================================================================

variable "user_name" {
  description = "Email address of the user to assign as workspace admin (must exist in Databricks account console)"
  type        = string
}

variable "workspace_id" {
  description = "Databricks workspace ID to assign the user to"
  type        = string
}

