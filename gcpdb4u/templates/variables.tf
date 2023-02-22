/* 
Before you begin please run the following command and make sure the right account is configured to use gcloud command.
account used by `gcloud auth list`
*/

/*
in case if you are NOT using a shared vpc than service and host project id will be same
host project hosts the vpc used by databricks
*/

# This SA needs to be precreated and added to accounts.gcp.databricks.com with an admin role
variable "databricks_workspace_creator_sa" {
    description = "Service Account used to create Databricks resources"
    type = string
    default = "terraform@labs-byovpc-test.iam.gserviceaccount.com"
}

# This user will be added to newly created workspace as an admin user. You need to do this so that there exists
# atleast one user with login access to the workspace
variable "databricks_admin_user" {
    description = "User Account to add to Databricks workspace with workspace admin role"
    type = string
    default = "bhavin.kukadia@databricks.com"
}

variable "project" {
    description = "GCP project where databricks data plane is created i.e GKE cluster and DBFS related GCS accounts"
    type = string
    default = "labs-byovpc-test"
}
variable "host_project" {
    description = "GCP host project where shared vpc resides. This is only applicable if you are using a shared vpc"
    type = string
    default = "labs-byovpc-test"
}
variable "databricks_account_id" {
    description = <<EOT
                Databricks accounts ID - From the account console (https://accounts.gcp.databricks.com), 
                click the user identity(your email) on the upper right corner.
                In the popup menu, the account ID is visible. Click the small copy icon to its right to copy it to the clipboard.
                EOT
    type = string
    default = "9fcbb245-7c44-4522-9870-e38324104cf8" #e11e38c5-a449-47b9-b37f-0fa36c821612
}
variable "databricks_workspace_provisioner_sa_alias" {
    description = "GCP Service Account used to create a databricks workspace. This will be created as part of workspace creation"
    type = string
    default = "databricks-workspace-creator"
}
variable "databricks_region" {
    description = "GCP region for a databricks workspace "
    type = string
    default = "us-central1"
}
variable "databricks_vpc_id" {
    description = "GCP VPC ID"
    type = string
    default = "tf-test-vpc"
}
variable "databricks_node_subnet" {
    description = "GCP primary subnet used by GKE nodes"
    type = string
    default = "tf-node-subnet"
}
variable "databricks_pod_subnet" {
    description = "GCP secondary subnet1 used by pods"
    type = string
    default = "tf-pod-subnet"
}
variable "databricks_service_subnet" {
    description = "GCP secondary subnet2 used by service, the service in this case is the databricks api service that runs on each driver"
    type = string
    default = "tf-service-subnet"
}
variable "databricks_gke_master_ip_range" {
    description = "GKE master ip range"
    type = string
    default = "10.39.0.0/28"
}