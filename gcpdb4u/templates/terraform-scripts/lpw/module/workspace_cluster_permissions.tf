

resource "databricks_permissions" "policy_usage" {
  provider = databricks.workspace
  ***REMOVED*** MODIFICATION - This resource manages cluster policy permissions across all defined cluster policies.
  ***REMOVED*** It ensures that Databricks workspace access is centrally controlled for all policy usage, 
  ***REMOVED*** granting group/role permissions as defined in the local.cluster_policy_permissions_map variable.
  ***REMOVED*** Loop over all `databricks_cluster_policy.this` instances - only when workspace resources are provisioned
  for_each = var.provision_workspace_resources ? databricks_cluster_policy.this : {}

  ***REMOVED*** Assign the correct `cluster_policy_id` to each permission
  cluster_policy_id = each.value.id

  ***REMOVED*** Define the access control for the groups
  dynamic "access_control" {
    for_each = flatten([for perm in local.cluster_policy_permissions_map : [for group in perm.group : { group = group, role = perm.role }]])
    content {
      group_name       = access_control.value.group
      permission_level = upper(access_control.value.role)
    }
  }
  ***REMOVED*** MODIFICATION - The above "databricks_permissions.policy_usage" resource assigns permissions to all cluster policies
  ***REMOVED*** in the workspace (not just the default/shared one) for the specified groups and roles in local.cluster_policy_permissions_map.
  ***REMOVED*** This ensures that access controls for compute cluster policies are consistent and managed centrally across all policies.
  depends_on = [
    null_resource.wait_for_workspace_running,
    databricks_mws_permission_assignment.add_group_role_user,
    databricks_mws_permission_assignment.add_group_role_admin
  ]
}



data "databricks_cluster_policy" "shared" {
  ***REMOVED*** MODIFICATION - This data block retrieves the Databricks cluster policy named "Shared Compute"
  ***REMOVED*** so that it can be used for assigning permissions to authorized groups. 
  ***REMOVED*** By using a data source with a dependency on cluster policy creation and workspace readiness,
  ***REMOVED*** this ensures that permission assignments for the shared compute policy are executed
  ***REMOVED*** only after the policy exists and the workspace is in a RUNNING state.
  count      = var.provision_workspace_resources ? 1 : 0
  provider   = databricks.workspace
  name       = "Shared Compute"
  depends_on = [databricks_cluster_policy.shared_compute, null_resource.wait_for_workspace_running]
}



resource "databricks_permissions" "shared_cluster_policy_usage" {
  provider = databricks.workspace

  ***REMOVED*** MODIFICATION - This resource applies permissions for the Databricks "Shared Compute" cluster policy,
  ***REMOVED*** but only for those groups in local.cluster_policy_permissions_map that have shared_compute_access set to "true".
  ***REMOVED*** The access_control block below ensures that only these groups/roles are granted access on the shared cluster policy.
  ***REMOVED*** Only create the resource if workspace resources are provisioned and there's at least one entry with shared_computer_access = "true"
  count = (var.provision_workspace_resources && length([for perm in local.cluster_policy_permissions_map : perm if perm.shared_compute_access == "true"]) > 0) ? 1 : 0

  cluster_policy_id = data.databricks_cluster_policy.shared[0].id

  ***REMOVED*** Define the access control for only the groups with shared_computer_access = "true"
  dynamic "access_control" {
    for_each = flatten([
      for perm in local.cluster_policy_permissions_map : [
        for group in perm.group : {
          group = group,
          role  = perm.role
        } if perm.shared_compute_access == "true"
      ]
    ])
    content {
      group_name       = access_control.value.group
      permission_level = upper(access_control.value.role)
    }
  }

  ***REMOVED*** MODIFICATION - This resource block applies fine-grained access control to the Databricks "Shared Compute" cluster policy.
  ***REMOVED*** Only groups explicitly configured with shared_compute_access = "true" in the cluster_policy_permissions_map are granted the respective role on the shared policy.
  depends_on = [
    null_resource.wait_for_workspace_running,
    databricks_mws_permission_assignment.add_group_role_user,
    databricks_mws_permission_assignment.add_group_role_admin
  ]
}



