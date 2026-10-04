# Credential-free tests (mock provider): terraform init && terraform test

mock_provider "databricks" {
  alias = "account"
}

variables {
  location             = "eastus2"
  workspace_prefix     = "test"
  workspace_id_numeric = "1111111111111111"
}

run "default_has_no_network_policy" {
  command = plan

  assert {
    condition     = length(databricks_account_network_policy.this) == 0 && length(databricks_workspace_network_option.this) == 0
    error_message = "network policy must be opt-in"
  }
}

run "enabled_policy_is_restricted_and_enforced" {
  command = plan

  variables {
    enable_network_policy         = true
    allowed_internet_destinations = ["pypi.org"]
  }

  assert {
    condition     = databricks_account_network_policy.this[0].egress.network_access.restriction_mode == "RESTRICTED_ACCESS"
    error_message = "policy must use RESTRICTED_ACCESS"
  }
  assert {
    condition     = databricks_account_network_policy.this[0].egress.network_access.policy_enforcement.enforcement_mode == "ENFORCED"
    error_message = "policy must be ENFORCED by default (DRY_RUN does not block)"
  }
  assert {
    condition     = databricks_account_network_policy.this[0].egress.network_access.allowed_internet_destinations[0].destination == "pypi.org"
    error_message = "allowed destination missing"
  }
  assert {
    condition     = length(databricks_workspace_network_option.this) == 1
    error_message = "policy must be assigned to the workspace"
  }
}

run "rejects_unknown_enforcement_mode" {
  command = plan

  variables {
    enable_network_policy           = true
    network_policy_enforcement_mode = "OFF"
  }

  expect_failures = [var.network_policy_enforcement_mode]
}
