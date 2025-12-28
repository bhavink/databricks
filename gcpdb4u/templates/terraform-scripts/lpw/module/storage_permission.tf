resource "google_storage_bucket_iam_member" "unity_cred_admin_internal" {
  ***REMOVED*** MODIFICATION - This resource grants the Databricks GCP service account "roles/storage.objectAdmin" on the designated internal GCS bucket, 
  ***REMOVED*** enabling Unity Catalog storage credential management. Only applied for non-external (internal) projects. 
  ***REMOVED*** See also: unity_cred_admin_external for external buckets.
  for_each = var.external_project ? {} : (var.provision_workspace_resources ? local.unity_catalog_config_map : {})

  provider = google.internal

  role   = "roles/storage.objectAdmin"
  bucket = each.value.external_bucket
  member = "serviceAccount:${databricks_storage_credential.this[each.key].databricks_gcp_service_account[0].email}"
  ***REMOVED*** MODIFICATION - added null_resource.wait_for_workspace_running dependency to make sure that workspace is in running state
  depends_on = [databricks_storage_credential.this, google_storage_bucket.internal_bucket, null_resource.wait_for_workspace_running]
}

resource "google_storage_bucket_iam_member" "unity_cred_admin_external" {
  ***REMOVED*** MODIFICATION - This resource grants the Databricks GCP service account "roles/storage.objectAdmin" on the designated external GCS bucket,
  ***REMOVED*** enabling Unity Catalog storage credential management. Only applied for external (shared) buckets/projects.
  ***REMOVED*** See also: unity_cred_admin_internal for internal buckets.
  for_each = var.external_project ? (var.provision_workspace_resources ? local.unity_catalog_config_map : {}) : {}
  provider = google.external
  role     = "roles/storage.objectAdmin"
  bucket   = each.value.external_bucket
  member   = "serviceAccount:${databricks_storage_credential.this[each.key].databricks_gcp_service_account[0].email}"
  ***REMOVED*** MODIFICATION - added null_resource.wait_for_workspace_running dependency to make sure that workspace is in running state
  depends_on = [databricks_storage_credential.this, google_storage_bucket.external_bucket, null_resource.wait_for_workspace_running]
}

resource "google_storage_bucket_iam_member" "unity_cred_reader_internal" {
  ***REMOVED*** MODIFICATION - This resource grants the Databricks GCP service account "roles/storage.legacyBucketReader" on the designated internal GCS bucket,
  ***REMOVED*** enabling Databricks clusters to read from GCS buckets managed within the same (internal) project. 
  ***REMOVED*** Only applied for non-external (internal) projects. See also: unity_cred_reader_external for external buckets.
  for_each = var.external_project ? {} : (var.provision_workspace_resources ? local.unity_catalog_config_map : {})
  provider = google.internal
  role     = "roles/storage.legacyBucketReader"
  bucket   = each.value.external_bucket
  member   = "serviceAccount:${databricks_storage_credential.this[each.key].databricks_gcp_service_account[0].email}"
  ***REMOVED*** MODIFICATION - added null_resource.wait_for_workspace_running dependency to make sure that workspace is in running state
  depends_on = [databricks_storage_credential.this, google_storage_bucket.internal_bucket, null_resource.wait_for_workspace_running]
}

resource "google_storage_bucket_iam_member" "unity_cred_reader_external" {
  ***REMOVED*** MODIFICATION - This resource grants the Databricks GCP service account "roles/storage.legacyBucketReader" on the designated external GCS bucket,
  ***REMOVED*** enabling Databricks clusters to read from GCS buckets managed in an external (shared) project.
  ***REMOVED*** Only applied for external (shared) buckets/projects. See also: unity_cred_reader_internal for internal buckets.
  for_each = var.external_project ? (var.provision_workspace_resources ? local.unity_catalog_config_map : {}) : {}
  provider = google.external
  role     = "roles/storage.legacyBucketReader"
  bucket   = each.value.external_bucket
  member   = "serviceAccount:${databricks_storage_credential.this[each.key].databricks_gcp_service_account[0].email}"
  ***REMOVED*** MODIFICATION - added null_resource.wait_for_workspace_running dependency to make sure that workspace is in running state
  depends_on = [databricks_storage_credential.this, google_storage_bucket.external_bucket, null_resource.wait_for_workspace_running]
}