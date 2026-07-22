# The workspace emits its compute GSA (gcp_workspace_sa) at creation, but GCP IAM
# is eventually consistent — binding roles to the brand-new SA in the same apply
# can 400 "service account does not exist". Wait for it to propagate before the
# grants below. 60s is comfortably above the typical propagation window.
resource "time_sleep" "wait_for_workspace_gsa" {
  depends_on      = [databricks_mws_workspaces.databricks_workspace]
  create_duration = "60s"
  # Re-trigger the wait if the workspace (hence its GSA) is ever recreated.
  triggers = {
    gsa = databricks_mws_workspaces.databricks_workspace.gcp_workspace_sa
  }
}

# Databricks workspace compute service account project-level role
resource "google_project_iam_member" "databricks_project_role_assignment" {
  depends_on = [time_sleep.wait_for_workspace_gsa]
  project    = var.google_project_id
  role       = module.prereqs.project_role_id
  member     = "serviceAccount:${databricks_mws_workspaces.databricks_workspace.gcp_workspace_sa}"
}

# Databricks workspace compute service account project-level resource role
resource "google_project_iam_member" "databricks_resource_role_assignment" {
  depends_on = [time_sleep.wait_for_workspace_gsa]
  project    = var.google_project_id
  role       = module.prereqs.resource_role_id
  member     = "serviceAccount:${databricks_mws_workspaces.databricks_workspace.gcp_workspace_sa}"

  condition {
    title       = "databricks-${databricks_mws_workspaces.databricks_workspace.workspace_id}-iam-condition-v2"
    description = "DO NOT DELETE - Restrict to Databricks-managed resources for this workspace"
    expression  = "resource.name.extract('{x}databricks') != '' && resource.name.extract('{x}${databricks_mws_workspaces.databricks_workspace.workspace_id}') != ''"
  }
}


# Databricks workspace compute service account subnet-level network role
resource "google_compute_subnetwork_iam_member" "databricks_network_role_assignment" {
  depends_on = [time_sleep.wait_for_workspace_gsa]
  project    = local.vpc_project_id
  region     = var.google_region
  subnetwork = module.prereqs.subnet_name
  role       = module.prereqs.network_role_id
  member     = "serviceAccount:${databricks_mws_workspaces.databricks_workspace.gcp_workspace_sa}"
}
