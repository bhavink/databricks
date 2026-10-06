# Credential-free tests (mock providers): terraform init -backend=false && terraform test

mock_provider "databricks" {
  alias = "accounts"
}

variables {
  databricks_account_id = "00000000-0000-0000-0000-000000000000"
  workspace_name        = "labs-serverless"
  region                = "us-west-2"
}

run "serverless_workspace_without_network" {
  command = plan

  assert {
    condition     = databricks_mws_workspaces.this.compute_mode == "SERVERLESS"
    error_message = "the workspace must be serverless"
  }
  assert {
    condition     = databricks_mws_workspaces.this.aws_region == "us-west-2"
    error_message = "the workspace is created in the given region"
  }
  assert {
    condition = (databricks_mws_workspaces.this.network_id == null
      && databricks_mws_workspaces.this.credentials_id == null
    && databricks_mws_workspaces.this.private_access_settings_id == null)
    error_message = "a serverless workspace has no customer network, role or private access settings"
  }
}

run "rejects_govcloud" {
  command = plan

  variables {
    region = "us-gov-west-1"
  }

  expect_failures = [var.region]
}
