variable "databricks_account_id" {}
variable "databricks_account_console_url" {}
variable "databricks_workspace_name" {}
variable "databricks_admin_user" {}
variable "google_shared_vpc_project" {}
variable "google_vpc_id" {}
variable "node_subnet" {}

***REMOVED*** if you are bringing pre-created key then uncomment the following line in the workspace.auto.tfvars file 
***REMOVED*** and update it with your key resource id

***REMOVED*** cmek_resource_id = "projects/[project-id]/locations/[region]]/keyRings/[key-ring-name]/cryptoKeys/[key-name]"

***REMOVED*** for more details on customer managed keys please refer to https://docs.gcp.databricks.com/security/keys/customer-managed-keys.html
***REMOVED*** we will be using same key for managed and unmanaged services encryption.


***REMOVED*** after updating the workspace.auto.tfvars file uncomment the following line

***REMOVED*** variable "cmek_resource_id" {}

data "google_client_openid_userinfo" "me" {}
data "google_client_config" "current" {}


***REMOVED******REMOVED******REMOVED*** If you've pre created the key then please comment following blocks

***REMOVED******REMOVED******REMOVED*** Create key block start

***REMOVED*** create key ring
resource "google_kms_key_ring" "databricks_key_ring" {
  name     = "databricks-keyring"
  location = var.google_region
}

***REMOVED*** create key used for encryption
resource "google_kms_crypto_key" "databricks_key" {
  name       = "databricks-key"
  key_ring   = google_kms_key_ring.databricks_key_ring.id
  purpose    = "ENCRYPT_DECRYPT"
  rotation_period = "31536000s" ***REMOVED*** Set rotation period to 1 year in seconds, need to be greater than 1 day
  
  ***REMOVED*** same key used for databricks managed and unmanaged storage
}


***REMOVED*** Output the key self_link for reference
output "key_self_link" {
  value = google_kms_crypto_key.databricks_key.id
}

locals {
  cmek_resource_id = google_kms_crypto_key.databricks_key.id
}

***REMOVED******REMOVED******REMOVED*** Create key block end



resource "databricks_mws_customer_managed_keys" "this" {
        depends_on = [ google_kms_crypto_key.databricks_key ]
        provider = databricks.accounts
				account_id   = var.databricks_account_id
				gcp_key_info {
					kms_key_id   = local.cmek_resource_id ***REMOVED*** change this to var.cmek_resource_id if using a pre-created key
				}
				use_cases = ["STORAGE","MANAGED"]
			      lifecycle {
              ignore_changes = all
        }
}

***REMOVED*** Random suffix for databricks network and workspace
resource "random_string" "databricks_suffix" {
  special = false
  upper   = false
  length  = 2
}

***REMOVED*** Provision databricks network configuration
resource "databricks_mws_networks" "databricks_network" {
  provider     = databricks.accounts
  account_id   = var.databricks_account_id
  ***REMOVED*** name needs to be of length 3-30 incuding [a-z,A-Z,-_]
  network_name = "${var.google_shared_vpc_project}-nw-${random_string.databricks_suffix.result}"
  gcp_network_info {
    network_project_id    = var.google_shared_vpc_project
    vpc_id                = var.google_vpc_id
    subnet_id             = var.node_subnet
    subnet_region         = var.google_region
  }
}
***REMOVED*** Provision databricks workspace in a customer managed vpc
***REMOVED*** https://docs.gcp.databricks.com/administration-guide/account-settings-gcp/workspaces.html***REMOVED***create-a-workspace-using-the-account-console

resource "databricks_mws_workspaces" "databricks_workspace" {
  provider       = databricks.accounts
  account_id     = var.databricks_account_id
  workspace_name = var.databricks_workspace_name
  location       = var.google_region
  cloud_resource_container {
    gcp {
      project_id = var.google_project_name
    }
  }
  network_id = databricks_mws_networks.databricks_network.network_id
  GCE_config {
    connectivity_type = "PRIVATE_NODE_PUBLIC_MASTER"
    master_ip_range   = var.GCE_master_ip_range
  }
  storage_customer_managed_key_id = databricks_mws_customer_managed_keys.this.customer_managed_key_id
}



data "databricks_group" "admins" {
  depends_on   = [ databricks_mws_workspaces.databricks_workspace ]
  provider     = databricks.workspace
  display_name = "admins"
}

resource "databricks_user" "me" {
  depends_on = [ databricks_mws_workspaces.databricks_workspace ]
  provider   = databricks.workspace
  user_name  = data.google_client_openid_userinfo.me.email
}

resource "databricks_group_member" "allow_me_to_login" {
  depends_on = [ databricks_mws_workspaces.databricks_workspace ]
  provider   = databricks.workspace
  group_id   = data.databricks_group.admins.id
  member_id  = databricks_user.me.id
}

output "workspace_url" {
  value = databricks_mws_workspaces.databricks_workspace.workspace_url
}