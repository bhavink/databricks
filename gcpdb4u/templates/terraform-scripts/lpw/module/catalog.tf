resource "databricks_storage_credential" "this" {
  provider     = databricks.workspace
  for_each     = var.provision_workspace_resources ? local.unity_catalog_config_map : {}
  metastore_id = var.metastore_id == "" ? local.databricks_metastore_id[var.google_region] : var.metastore_id
  name         = "${each.value.name}-storage-creds"
  databricks_gcp_service_account {}
  # MODIFICATION: Changed to OPEN mode for explicit workspace binding
  # Reason: ISOLATED mode auto-binds and conflicts with explicit databricks_workspace_binding resources
  isolation_mode = "ISOLATION_MODE_OPEN"
  # MODIFICATION - This is what you used earlier
  # isolation_mode = each.value.shared == "false" ? "ISOLATION_MODE_ISOLATED" : each.value.shared == "true" ? "ISOLATION_MODE_OPEN" : "ISOLATION_MODE_OPEN"
  comment       = "Managed by TF"
  force_destroy = true
  # MODIFICATION - added null_resource.wait_for_workspace_running dependency to make sure that workspace is in running state
  depends_on = [databricks_metastore_assignment.this, null_resource.wait_for_workspace_running]
}

resource "databricks_external_location" "external_location" {
  provider = databricks.workspace
  for_each = var.provision_workspace_resources ? local.unity_catalog_config_map : {}
  name     = "${each.value.name}-ext-location"
  ## Below code is creating a bucket, we can also pass the bucket url as a variables var.gs_bucket_url
  #url = element(local.external_buckets_url, index(local.unity_catalog_name_list, each.value))
  url             = var.external_project ? "gs://${data.google_storage_bucket.external_bucket[each.key].name}" : "gs://${data.google_storage_bucket.internal_bucket[each.key].name}"
  credential_name = databricks_storage_credential.this[each.key].id
  comment         = "Managed by TF"
  # MODIFICATION: Changed to OPEN mode for explicit workspace binding
  # Reason: ISOLATED mode auto-binds and conflicts with explicit databricks_workspace_binding resources
  isolation_mode = "ISOLATION_MODE_OPEN"
  force_destroy  = true
  # MODIFICATION: Added IAM dependencies
  # Reason: Ensure GCS IAM permissions exist before Databricks validates bucket access
  # Added null_resource.wait_for_workspace_running dependency to make sure that workspace is in running state
  depends_on = [
    databricks_metastore_assignment.this,
    google_storage_bucket_iam_member.unity_cred_admin_internal,
    google_storage_bucket_iam_member.unity_cred_admin_external,
    google_storage_bucket_iam_member.unity_cred_reader_internal,
    google_storage_bucket_iam_member.unity_cred_reader_external,
    databricks_storage_credential.this,
    null_resource.wait_for_workspace_running
  ]
}

resource "databricks_catalog" "workspace_catalog" {
  provider = databricks.workspace
  for_each = var.provision_workspace_resources ? local.unity_catalog_config_map : {}
  name     = each.value.name
  #storage_root = element(local.external_buckets_url, index(local.unity_catalog_name_list, each.value))
  storage_root = var.external_project ? "gs://${data.google_storage_bucket.external_bucket[each.key].name}" : "gs://${data.google_storage_bucket.internal_bucket[each.key].name}"
  #isolation_mode - (Optional) Whether the catalog is accessible from all workspaces or a specific set of workspaces. 
  #Can be ISOLATED or OPEN. Setting the catalog to ISOLATED will automatically allow access from the current workspace.
  # MODIFICATION: Changed to OPEN mode for explicit workspace binding
  # Reason: ISOLATED mode auto-binds, we want explicit control via databricks_workspace_binding resources
  isolation_mode = "OPEN"
  comment        = "Managed by Terraform"
  force_destroy  = true
  # MODIFICATION - added null_resource.wait_for_workspace_running dependency to make sure that workspace is in running state
  depends_on = [
    databricks_external_location.external_location,
  null_resource.wait_for_workspace_running]
}
