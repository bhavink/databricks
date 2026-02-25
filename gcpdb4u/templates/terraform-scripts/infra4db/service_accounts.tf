# Instead of using the default compute engine GSA, databricks uses "databricks-compute@{workspace-project}.iam.gserviceaccount.com" 
# as the default compute-engine GSA attached to every VM launched by Databricks 
# in your GCP project. The naming pattern is required i.e "databricks-compute"

resource "google_service_account" "databricks_compute" {
  # count        = try(data.google_service_account.existing_sa.email, null) != null ? 0 : 1
  account_id   = "databricks-compute"
  display_name = "Databricks Compute Service Account"
}



# Assign IAM roles only if the SA was created
resource "google_project_iam_member" "log_writer" {
  #  count  = length(google_service_account.databricks_compute) > 0 ? 1 : 0
  project = var.vpc_project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.databricks_compute.email}"
}

resource "google_project_iam_member" "metric_writer" {
  # count  = length(google_service_account.databricks_compute) > 0 ? 1 : 0
  project = var.vpc_project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.databricks_compute.email}"
}
