***REMOVED*** For latest role requirements please refer
***REMOVED*** https://docs.databricks.com/gcp/en/admin/cloud-configurations/gcp/permissions
resource "google_project_iam_custom_role" "databricks_creator_role" {
  role_id     = "databricks.creator.role.project.v2"  ***REMOVED*** Unique ID for the role
  title       = "Databricks Workspace Creator Role Required For Project"  ***REMOVED*** Display name for the role
  description = "A custom role for creating workspaces and managing related resources."

  permissions = [
    "iam.roles.create", 
    "iam.roles.update", ***REMOVED***optional
    "iam.roles.delete", ***REMOVED***optional
    "iam.roles.get",
    "iam.serviceAccounts.create", ***REMOVED***not required if you pre-create databricks-compute GSA as shown in service_accounts.tf
    "iam.serviceAccounts.get", 
    "iam.serviceAccounts.getIamPolicy",
    "iam.serviceAccounts.setIamPolicy",
    "resourcemanager.projects.get",
    "resourcemanager.projects.getIamPolicy",
    "resourcemanager.projects.setIamPolicy",
    "serviceusage.services.get",
    "serviceusage.services.list",
    "serviceusage.services.enable" ***REMOVED***optional if required googleapi's are already enabled
  ]

  ***REMOVED*** Specify the project where the role will be created
  project = var.vpc_project_id  ***REMOVED*** if vpc resides in the same project then 
}

resource "google_project_iam_custom_role" "databricks_creator_role_vpc" {
  role_id     = "databricks.creator.role.vpc.v2"  ***REMOVED*** Unique ID for the role
  title       = "Databricks Workspace Creator Role Required For VPC Project"  ***REMOVED*** Display name for the role
  description = "Required for VPC project"  ***REMOVED*** Description for the role

  permissions = [
    "compute.projects.get",
    "compute.networks.updatePolicy",
    "compute.networks.get",
    "compute.subnetworks.get",
    "compute.subnetworks.getIamPolicy",
    "compute.subnetworks.setIamPolicy",
    "compute.forwardingRules.get", ***REMOVED*** for psc ws only
    "compute.forwardingRules.list", ***REMOVED*** for psc ws only
    "compute.firewalls.get",
    "compute.firewalls.create",
    "serviceusage.services.list",
    "serviceusage.services.get",
    "resourcemanager.projects.getIamPolicy",
    "resourcemanager.projects.get",
    "iam.roles.update", ***REMOVED*** optional
    "iam.roles.get",
    "iam.roles.create",
    "iam.roles.delete" ***REMOVED*** optional
  ]

  ***REMOVED*** Specify the project where the role will be created
  project = var.vpc_project_id  ***REMOVED*** Ensure you have a variable for project_id defined
}