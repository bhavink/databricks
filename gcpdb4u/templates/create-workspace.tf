/*
account used to create databriks workspace
prior to running this script, make sure that this SA exists as a databricks accounts admin by visiting 
https://accounts.gcp.databricks.com > User Management > Search for the SA email and verify its role
*/

/* 
account used by `gcloud auth login`
you may want to run this command on your local system to make sure identity used by gcloud
here's an example of identity used, this identity will be impersonated by the servie account
this script will be executed as [servie account]. 
*/
variable "delegate_from" {default="bhavin.kukadia@databricks.com"}

# service account used to create the workspace
variable "databricks_google_service_account" { default = "test-ws-sa@labs-byovpc-test.iam.gserviceaccount.com"}

# daatbricks account id available on accounts console > clicked on the logged in user email (top right corner)
variable "databricks_account_id" { default = "e11e38c5-xyz-821612" }

/*
in case if you are NOT using a shared vpc than service and host project id will be same
host project hosts the vpc used by databricks
*/
variable "google_host_project" { default = "labs-byovpc-test" }

# this is where databricks managed gke is created
variable "google_service_project" { default = "labs-byovpc-test" }

variable "google_region" { default = "us-central1" }

variable "vpc_id" {default = "tf-test-vpc"}
variable "node_subnet" {default = "tf-node-subnet"}
variable "pod_subnet" {default = "tf-pod-subnet"}
variable "service_subnet" {default = "tf-service-subnet"}
variable "gke_master_ip_range" {default = "10.39.0.0/28"}

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
}

provider "databricks" {
  host                   = "https://accounts.gcp.databricks.com"
  google_service_account = var.databricks_google_service_account
}

data "google_client_openid_userinfo" "me" {
}

resource "random_string" "suffix" {
  special = false
  upper   = false
  length  = 6
}
resource "databricks_mws_networks" "this" {
  account_id     = var.databricks_account_id
  network_name = "bk-tf-nw-config${random_string.suffix.result}"
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
  workspace_name = "bk-tf-${random_string.suffix.result}"
  location = var.google_region
    gke_config {
      connectivity_type = "PRIVATE_NODE_PUBLIC_MASTER"
      master_ip_range = "${var.gke_master_ip_range}"
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



/*
Now, after you’ve declared a workspace, 
you should provision the infrastructure within that workspace. 
The following configuration declares the ability for your user principal 
to login into this workspace, as at this point only the var.
databricks_google_service_account can log into that workspace via API through OIDC token. 
This also adds administrative access to your user, which you don’t have by default. 
Please pay special attention to the fact that we’re using multiple instances of databricks
provider within the same Terraform module and therefore each resource 
block must include provider attribute to refer to workspace instance. 
If you’re noticing “could not obtain OIDC token. impersonate: an audience 
must be provided” errors, then it means that there’s no 
value in databricks_mws_workspaces.this.workspace_url yet 
and you have to apply this configuration either through different modules or apply steps.
*/

provider "databricks" {
 alias                  = "workspace"
 host                   = databricks_mws_workspaces.this.workspace_url
 google_service_account = var.databricks_google_service_account
}


data "databricks_group" "admins" {
 depends_on   = [databricks_mws_workspaces.this]
 provider     = databricks.workspace
 display_name = "admins"
}


resource "databricks_user" "me" {
 depends_on = [databricks_mws_workspaces.this]


 provider  = databricks.workspace
 user_name = data.google_client_openid_userinfo.me.email
}


resource "databricks_group_member" "allow_me_to_login" {
 depends_on = [databricks_mws_workspaces.this]
 
 provider  = databricks.workspace
 group_id  = data.databricks_group.admins.id
 member_id = databricks_user.me.id
}


/*
Once your user access is defined, 
you’ll want to declare a couple of related things within 
workspace - a notebook in the home folder, smallest possible 
Databricks cluster and a job that executes that notebook on that cluster.
*/

data "databricks_current_user" "me" {
 depends_on = [databricks_mws_workspaces.this]


 provider = databricks.workspace
}


data "databricks_spark_version" "latest" {
 depends_on   = [databricks_mws_workspaces.this]
 
 provider = databricks.workspace
}


data "databricks_node_type" "smallest" {
 depends_on = [databricks_mws_workspaces.this]
 provider   = databricks.workspace
 local_disk = true
}


resource "databricks_notebook" "this" {
 depends_on = [databricks_mws_workspaces.this]


 provider = databricks.workspace
 path     = "${data.databricks_current_user.me.home}/Terraform"
 language = "PYTHON"
 content_base64 = base64encode(<<-EOT
   # created from ${abspath(path.module)}
   display(spark.range(10))
   EOT
 )
}


resource "databricks_cluster" "this" {
 depends_on              = [databricks_mws_workspaces.this]
 provider                = databricks.workspace
 cluster_name            = "Shared Autoscaling  (by ${data.databricks_current_user.me.alphanumeric})"
 spark_version           = data.databricks_spark_version.latest.id
 node_type_id            = data.databricks_node_type.smallest.id
 autotermination_minutes = 20
 autoscale {
   min_workers = 1
   max_workers = 2
 }
}

resource "databricks_job" "this" {
 depends_on          = [databricks_mws_workspaces.this]
 provider            = databricks.workspace
 name                = "Terraform Demo (${data.databricks_current_user.me.alphanumeric})"
 existing_cluster_id = databricks_cluster.this.id
 notebook_task {
   notebook_path = databricks_notebook.this.path
 }
}

output "notebook_url" {
 value = databricks_notebook.this.url
}

output "job_url" {
 value = databricks_job.this.url
}
