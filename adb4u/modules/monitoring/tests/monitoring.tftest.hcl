# Credential-free tests (mock provider): terraform init && terraform test

mock_provider "azurerm" {
  override_data {
    target = data.azurerm_monitor_diagnostic_categories.workspace
    values = {
      log_category_types = ["accounts", "clusters", "unityCatalog"]
    }
  }
}

variables {
  workspace_id               = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Databricks/workspaces/ws"
  log_analytics_workspace_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.OperationalInsights/workspaces/law"
}

run "enables_every_discovered_category" {
  command = apply

  assert {
    condition     = length(azurerm_monitor_diagnostic_setting.workspace.enabled_log) == 3
    error_message = "every discovered log category must be enabled"
  }
  assert {
    condition     = azurerm_monitor_diagnostic_setting.workspace.log_analytics_workspace_id == var.log_analytics_workspace_id
    error_message = "Log Analytics destination not set"
  }
}

run "requires_a_destination" {
  command = plan

  variables {
    log_analytics_workspace_id = ""
  }

  expect_failures = [azurerm_monitor_diagnostic_setting.workspace]
}
