variable "google_service_account_email" {}
variable "google_project_name" {}
variable "google_region" {}
variable "google_shared_vpc_project" {}

terraform {
  required_providers {
    databricks = {
      source = "databricks/databricks"
      version = ">=1.24.0"
    }
    google = {
      source = "hashicorp/google"
    }
  }
}

provider "google" {
  project = var.google_project_name
  region  = var.google_region
}

provider "google" {
  alias = "vpc_project"
  project = var.google_shared_vpc_project
  region  = var.google_region
}


provider "databricks" {
  alias                  = "accounts"
  host                   = "https://accounts.gcp.databricks.com"
  google_service_account = var.google_service_account_email
}

provider "databricks" {
  alias                  = "workspace"
  host                   = databricks_mws_workspaces.databricks_workspace.workspace_url
  google_service_account = var.google_service_account_email
}