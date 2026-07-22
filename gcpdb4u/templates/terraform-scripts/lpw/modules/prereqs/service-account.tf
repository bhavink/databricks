# ------------------------------------------------------------------
# Databricks-compute service account (prereq).
# Used by all clusters in the workspace that do NOT have a custom SA attached.
# Kept at bare-minimum privilege: read-only Cloud Monitoring metrics.
#
# Cost: none. IAM bindings are free, and roles/monitoring.viewer is read-only
# (Monitoring bills on metric ingestion/writes, which this role cannot do).
# ------------------------------------------------------------------

resource "google_service_account" "databricks_compute" {
  project      = var.google_project_id
  account_id   = "databricks-compute"
  display_name = "Databricks Compute Service Account"
}

# Minimal, no-cost permission: view Cloud Monitoring metrics only.
resource "google_project_iam_member" "databricks_compute_metrics_viewer" {
  project = var.google_project_id
  role    = "roles/monitoring.viewer"
  member  = "serviceAccount:${google_service_account.databricks_compute.email}"
}

output "databricks_compute_sa_email" {
  description = "Email of the default Databricks-compute service account."
  value       = google_service_account.databricks_compute.email
}
