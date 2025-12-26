# ============================================================================
# User Assignment Module - Provider Configuration
# ============================================================================

terraform {
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.50"
    }
  }
}

