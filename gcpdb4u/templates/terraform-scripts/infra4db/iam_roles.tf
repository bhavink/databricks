# For latest role requirements please refer
# https://docs.databricks.com/gcp/en/admin/cloud-configurations/gcp/permissions
resource "google_project_iam_custom_role" "databricks_creator_role" {
  role_id     = "databricks.creator.role.project.v2"                     # Unique ID for the role
  title       = "Databricks Workspace Creator Role Required For Project" # Display name for the role
  description = "A custom role for creating workspaces and managing related resources."

  permissions = [
    "iam.roles.create",
    "iam.roles.update",
    "iam.roles.delete",
    "iam.roles.get",
    "iam.serviceAccounts.create", #not required if you pre-create databricks-compute GSA as shown in service_accounts.tf
    "iam.serviceAccounts.get",
    "iam.serviceAccounts.getIamPolicy",
    "iam.serviceAccounts.setIamPolicy",
    "resourcemanager.projects.get",
    "resourcemanager.projects.getIamPolicy",
    "resourcemanager.projects.setIamPolicy",
    "serviceusage.services.get",
    "serviceusage.services.list",
    "serviceusage.services.enable"
  ]

  # Specify the project where the role will be created
  project = var.vpc_project_id # if vpc resides in the same project then 
}

resource "google_project_iam_custom_role" "databricks_creator_role_vpc" {
  role_id     = "databricks.creator.role.vpc.v2"                             # Unique ID for the role
  title       = "Databricks Workspace Creator Role Required For VPC Project" # Display name for the role
  description = "Required for VPC project"                                   # Description for the role

  permissions = [
    "compute.projects.get",
    "compute.networks.updatePolicy",
    "compute.networks.get",
    "compute.subnetworks.get",
    "compute.subnetworks.getIamPolicy",
    "compute.subnetworks.setIamPolicy",
    "compute.forwardingRules.get",  # for psc ws only
    "compute.forwardingRules.list", # for psc ws only
    "compute.firewalls.get",
    "compute.firewalls.create",
    "serviceusage.services.list",
    "serviceusage.services.get",
    "resourcemanager.projects.getIamPolicy",
    "resourcemanager.projects.get",
    "iam.roles.update",
    "iam.roles.get",
    "iam.roles.create",
    "iam.roles.delete"
  ]

  # Specify the project where the role will be created
  project = var.vpc_project_id # Ensure you have a variable for project_id defined
}