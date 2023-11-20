variable "google_service_account_email" {}
variable "google_project_name" {}
variable "google_region" {}
variable "databricks_account_id" {}

terraform {
  required_providers {
    databricks = {
      source = "databricks/databricks"
      version = ">=1.29.0"
    }
    google = {
      source = "hashicorp/google"
    }

    random = {
      source = "hashicorp/random"
    }
  }
}

provider "google" {
  project = var.google_project_name
  region  = var.google_region
}

provider "databricks" {
  alias                  = "accounts"
  host                   = "https://accounts.gcp.databricks.com"
  google_service_account = var.google_service_account_email
  account_id = var.databricks_account_id
}

provider "databricks" {
  alias                  = "workspace"
  host                   = databricks_mws_workspaces.databricks_workspace.workspace_url
  google_service_account = var.google_service_account_email
}