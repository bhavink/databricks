resource "databricks_instance_pool" "compute_pools" {
  ***REMOVED*** MODIFICATION - This resource creates and manages Databricks instance pools for each compute type,
  ***REMOVED*** in accordance with pool configs and after workspace is confirmed RUNNING.
  for_each                              = var.provision_workspace_resources ? { for type in split(",", var.compute_types) : type => local.pool_configs[type] } : {}
  provider                              = databricks.workspace
  instance_pool_name                    = each.value.name
  min_idle_instances                    = 0
  max_capacity                          = each.value.max_capacity
  node_type_id                          = each.value.node_type
  idle_instance_autotermination_minutes = 10

  disk_spec {
    disk_type {
      ebs_volume_type = "GENERAL_PURPOSE_SSD"
    }
    disk_size  = 80
    disk_count = 1
  }
  ***REMOVED*** MODIFICATION - added null_resource.wait_for_workspace_running dependency to make sure that workspace is in running state
  depends_on = [null_resource.wait_for_workspace_running]
}

***REMOVED*** resource "databricks_cluster_policy" "policies" {
***REMOVED***   for_each   = local.policies
***REMOVED***   provider   = databricks.workspace
***REMOVED***   name       = each.key
***REMOVED***   definition = jsonencode(merge(each.value, local.common_policy, local.common_tags))
***REMOVED***   depends_on = [databricks_mws_workspaces.dbx_workspace]
***REMOVED*** }

resource "databricks_cluster_policy" "this" {
  ***REMOVED*** MODIFICATION - This resource manages custom cluster policies defined in local.cluster_policies_map.
  ***REMOVED*** It ensures that each required cluster policy for the workspace is created with the proper configuration,
  ***REMOVED*** combining policy values with standard defaults and tags for consistency. All policies depend on the workspace being in a RUNNING state.
  for_each   = local.cluster_policies_map
  provider   = databricks.workspace
  name       = "${each.value.type}_${each.value.name}"
  definition = jsonencode(merge(each.value.value, local.common_policy, local.common_tags))
  ***REMOVED*** MODIFICATION - added null_resource.wait_for_workspace_running dependency to make sure that workspace is in running state
  depends_on = [null_resource.wait_for_workspace_running]
}


resource "databricks_cluster_policy" "personal_vm" {
  ***REMOVED*** MODIFICATION - This resource ensures the Databricks "Personal Compute" cluster policy is managed via Terraform with policy family overrides
  ***REMOVED*** and applies local common tags, common policy config, a default compute timeout, and allowed node types for personal compute.
  count                              = var.provision_workspace_resources ? 1 : 0
  provider                           = databricks.workspace
  policy_family_id                   = "personal-vm"
  description                        = "personal compute overrided with terraform"
  policy_family_definition_overrides = jsonencode(merge(local.common_tags, local.common_policy, local.default_compute_timeout, local.personal_compute_node_types))
  name                               = "Personal Compute"
  ***REMOVED*** MODIFICATION - added null_resource.wait_for_workspace_running dependency to make sure that workspace is in running state
  depends_on = [null_resource.wait_for_workspace_running]
}

resource "databricks_cluster_policy" "shared_compute" {
  ***REMOVED*** MODIFICATION - This resource manages the Databricks "Shared Compute" cluster policy, which allows multiple users to share a pool of compute resources. 
  ***REMOVED*** The policy is managed through Terraform using policy family overrides and applies organization-wide settings and tags. 
  ***REMOVED*** It is only created if var.provision_workspace_resources is true, ensuring that shared policy does not exist until the workspace is ready.
  count                              = var.provision_workspace_resources ? 1 : 0
  provider                           = databricks.workspace
  policy_family_id                   = "shared-compute"
  description                        = "shared compute overrided with terraform"
  policy_family_definition_overrides = jsonencode(merge(local.common_tags, local.common_policy, local.default_compute_timeout))
  name                               = "Shared Compute"
  ***REMOVED*** MODIFICATION - added null_resource.wait_for_workspace_running dependency to make sure that workspace is in running state
  depends_on = [null_resource.wait_for_workspace_running]
}
