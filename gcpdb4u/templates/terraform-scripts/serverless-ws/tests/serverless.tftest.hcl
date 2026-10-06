# Credential-free tests (mock providers): terraform init -backend=false && terraform test

mock_provider "databricks" {
  alias = "accounts"
}

variables {
  databricks_account_id        = "00000000-0000-0000-0000-000000000000"
  google_service_account_email = "automation-sa@project.iam.gserviceaccount.com"
  databricks_workspace_name    = "labs-serverless"
  google_region                = "us-east4"
}

run "serverless_workspace_without_network" {
  command = plan

  assert {
    condition     = databricks_mws_workspaces.this.compute_mode == "SERVERLESS"
    error_message = "the workspace must be serverless"
  }
  assert {
    condition     = databricks_mws_workspaces.this.location == "us-east4"
    error_message = "the workspace is created in the given region"
  }
  assert {
    condition = (databricks_mws_workspaces.this.network_id == null
    && databricks_mws_workspaces.this.private_access_settings_id == null)
    error_message = "a serverless workspace has no customer network"
  }
}
