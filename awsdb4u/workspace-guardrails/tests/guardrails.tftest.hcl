# Credential-free tests (mock providers): terraform init -backend=false && terraform test

mock_provider "databricks" {
  alias = "accounts"
}
mock_provider "databricks" {
  alias = "workspace"
}

variables {
  databricks_account_id = "00000000-0000-0000-0000-000000000000"
  workspace_id          = "1111111111111111"
  workspace_url         = "https://dbc-11111111-1111.cloud.databricks.com"
  region                = "us-west-2"
}

run "bare_minimum_by_default" {
  command = apply

  assert {
    condition     = length(databricks_workspace_conf.this[0].custom_config) == 1 && databricks_workspace_conf.this[0].custom_config["enableIpAccessLists"] == "true"
    error_message = "IP access lists must be enabled by default, data-leak settings left alone"
  }
  assert {
    condition     = length(databricks_metastore_assignment.this) == 0
    error_message = "no metastore assignment unless a metastore_id is given"
  }
  assert {
    condition     = toset(keys(databricks_ip_access_list.this)) == toset(["office-allow"])
    error_message = "IP access lists come from ip_access_list.yaml"
  }
  assert {
    condition = (
      databricks_account_network_policy.this[0].egress.network_access.restriction_mode == "RESTRICTED_ACCESS"
      && databricks_account_network_policy.this[0].egress.network_access.policy_enforcement.enforcement_mode == "ENFORCED"
    )
    error_message = "serverless egress must be restricted and enforced by default"
  }
  assert {
    condition     = length(databricks_account_network_policy.this[0].egress.network_access.allowed_internet_destinations) == 2
    error_message = "allowed destinations come from network_policy.yaml"
  }
  assert {
    condition     = length(databricks_account_network_policy.this[0].network_policy_id) <= 32
    error_message = "network policy ids are limited to 32 characters"
  }
  assert {
    condition = (databricks_mws_ncc_binding.this[0].workspace_id == 1111111111111111
    && databricks_workspace_network_option.this[0].workspace_id == 1111111111111111)
    error_message = "NCC and network policy must be bound to the workspace"
  }
}

run "data_leak_and_metastore_options" {
  command = apply

  variables {
    disable_data_leak_features = true
    metastore_id               = "11111111-2222-3333-4444-555555555555"
  }

  assert {
    condition = (
      databricks_workspace_conf.this[0].custom_config["enableExportNotebook"] == "false"
      && databricks_workspace_conf.this[0].custom_config["enableResultsDownloading"] == "false"
      && databricks_workspace_conf.this[0].custom_config["enableNotebookTableClipboard"] == "false"
      && databricks_workspace_conf.this[0].custom_config["enableIpAccessLists"] == "true"
    )
    error_message = "data-leak settings are turned off in the same workspace_conf"
  }
  assert {
    condition     = databricks_metastore_assignment.this[0].workspace_id == 1111111111111111
    error_message = "the metastore is assigned to the workspace"
  }
}

run "shared_policy_is_bound_not_created" {
  command = apply

  variables {
    shared_network_policy_id = "org-serverless-policy"
  }

  assert {
    condition     = length(databricks_account_network_policy.this) == 0
    error_message = "no per-workspace policy when a shared one is given"
  }
  assert {
    condition     = databricks_workspace_network_option.this[0].network_policy_id == "org-serverless-policy"
    error_message = "the shared policy must be bound"
  }
}

run "controls_can_be_turned_off" {
  command = apply

  variables {
    enable_ip_access_list = false
    enable_network_policy = false
    enable_ncc            = false
  }

  assert {
    condition = (length(databricks_ip_access_list.this) == 0 && length(databricks_workspace_conf.this) == 0
      && length(databricks_account_network_policy.this) == 0
    && length(databricks_workspace_network_option.this) == 0 && length(databricks_mws_ncc_binding.this) == 0)
    error_message = "everything off means nothing created"
  }
}

run "rejects_bad_inputs" {
  command = plan

  variables {
    workspace_id                    = "dbc-1111"
    workspace_url                   = "dbc-1111.cloud.databricks.com"
    network_policy_enforcement_mode = "OFF"
  }

  expect_failures = [var.workspace_id, var.workspace_url, var.network_policy_enforcement_mode]
}
