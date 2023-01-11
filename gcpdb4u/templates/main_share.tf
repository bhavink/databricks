# please make sure to substitue place holer values with your project specific values
# for most upto date details, visit - https://registry.terraform.io/providers/databricks/databricks/latest/docs/guides/gcp-workspace
# the following script assumes that the vpc/subnet is precreated

variable "databricks_account_id" {
  default = "DATABRICKS ACCOUNT ID"
}

# host and service project could be same in case of using a single project
# where the vpc resides within the same project as databricks gke cluster

variable "google_host_project" {
  default = "GCP PROJECT WHERE VPC IS CREATED"
}

variable "google_service_project" {
  default = "GCP PROJECT WHERE WS RELATED GKE IS CREATED"
}

# make sure that the servcice account is added to databricks account console and is given accounts admin role
# https://docs.gcp.databricks.com/administration-guide/index.html
variable "databricks_google_service_account" {
    default = "XYZ@GCP_PROJECT.iam.gserviceaccount.com"
    }
variable "google_region" {default = "us-central1"}
variable "vpc_id" {default = "VPC ID"}
variable "node_subnet" {default = "PRIMARY SUBNET"}
variable "pod_subnet" {default = "SECONDARY SUBNET 1"}
variable "service_subnet" {default = "SECONDARY SUBNET 2"}

terraform {
  required_providers {
    databricks = {
      source = "databricks/databricks"
      version = "1.8.0"
    }
    google = {
      source  = "hashicorp/google"
    }
  }
}

provider "google" {
  project = var.google_service_project
  region  = var.google_region
  credentials = "PATH TO YOUR SERVCICE ACCOUNT CREDENTIAL.JSON FILE E.G. ./CREDS.JSON"
}
provider "databricks" {
  host = "https://accounts.gcp.databricks.com"
  google_credentials = "PATH TO YOUR SERVCICE ACCOUNT CREDENTIAL.JSON FILE E.G. ./CREDS.JSON"
}

data "google_client_config" "current" {
}

resource "random_string" "suffix" {
  special = false
  upper   = false
  length  = 6
}
resource "databricks_mws_networks" "this" {
  account_id     = var.databricks_account_id
  network_name = "NW-CONFIG-NAME-${random_string.suffix.result}"
  gcp_network_info {
    network_project_id = var.google_host_project
    vpc_id = var.vpc_id
    subnet_id = var.node_subnet
    subnet_region = var.google_region
    pod_ip_range_name = var.pod_subnet
    service_ip_range_name = var.service_subnet
  }
}

resource "databricks_mws_workspaces" "this" {
  account_id   = var.databricks_account_id
  network_id   = databricks_mws_networks.this.network_id 
  workspace_name = "WS-NAME-${random_string.suffix.result}"
  location = var.google_region
    gke_config {
      connectivity_type = "PRIVATE_NODE_PUBLIC_MASTER"
      master_ip_range = "x.x.x.x/28"
    }
    cloud_resource_container {
    gcp {
      project_id = var.google_service_project
    }
  }
}

output "databricks_network" {
  value = databricks_mws_networks.this.network_id
}
  output "databricks_host" {
  value = databricks_mws_workspaces.this.workspace_url
}