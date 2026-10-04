# Credential-free tests (mock providers): terraform init -backend=false && terraform test

mock_provider "azurerm" {
  mock_resource "azurerm_resource_group" {
    defaults = { id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-test" }
  }
  mock_resource "azurerm_virtual_network" {
    defaults = { id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-test/providers/Microsoft.Network/virtualNetworks/vnet" }
  }
  mock_resource "azurerm_subnet" {
    defaults = { id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-test/providers/Microsoft.Network/virtualNetworks/vnet/subnets/privatelink" }
  }
  mock_resource "azurerm_private_dns_zone" {
    defaults = { id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-test/providers/Microsoft.Network/privateDnsZones/privatelink.azuredatabricks.net" }
  }
  mock_data "azurerm_client_config" {
    defaults = {
      subscription_id = "00000000-0000-0000-0000-000000000000"
      object_id       = "00000000-0000-0000-0000-000000000002"
    }
  }
  mock_data "azurerm_monitor_diagnostic_categories" {
    defaults = { log_category_types = ["accounts", "clusters"] }
  }
}
mock_provider "azapi" {}
mock_provider "databricks" {}
mock_provider "databricks" {
  alias = "workspace"
}
mock_provider "null" {}
mock_provider "time" {}

override_resource {
  target = module.workspace.azapi_resource.this
  values = {
    id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-test/providers/Microsoft.Databricks/workspaces/test-workspace"
    output = {
      properties = {
        workspaceUrl = "adb-1111111111111111.11.azuredatabricks.net"
        workspaceId  = "1111111111111111"
      }
    }
  }
}

variables {
  workspace_prefix      = "test"
  location              = "eastus2"
  resource_group_name   = "rg-test"
  databricks_account_id = "00000000-0000-0000-0000-000000000000"
  metastore_id          = "00000000-0000-0000-0000-000000000001"
}

run "serverless_compute_mode_and_defaults" {
  command = apply

  assert {
    condition     = module.workspace.id != ""
    error_message = "workspace must be created by the official module"
  }
  assert {
    condition     = databricks_account_network_policy.this.egress.network_access.restriction_mode == "FULL_ACCESS"
    error_message = "network policy must default to full access"
  }
  assert {
    condition     = length(azurerm_private_endpoint.ui_api) == 0
    error_message = "no front-end private endpoint while public access is enabled"
  }
  assert {
    condition     = length(databricks_ip_access_list.allowed) == 0 && length(module.monitoring) == 0
    error_message = "optional features must be off by default"
  }
}

run "high_security" {
  command = apply

  variables {
    enable_public_network_access             = false
    enable_network_policy                    = true
    serverless_allowed_internet_destinations = ["pypi.org"]
    serverless_private_endpoint_storage_account_ids = [
      "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Storage/storageAccounts/stdata"
    ]
    managed_services_cmk_key_id = "https://kv-test.vault.azure.net/keys/cmk/0123456789abcdef"
    additional_workspace_config = {
      enableExportNotebook         = "false"
      enableResultsDownloading     = "false"
      enableNotebookTableClipboard = "false"
    }
  }

  assert {
    condition     = length(azurerm_private_endpoint.ui_api) == 1
    error_message = "front-end private endpoint required when public access is disabled"
  }
  assert {
    condition = (
      databricks_account_network_policy.this.egress.network_access.restriction_mode == "RESTRICTED_ACCESS"
      && databricks_account_network_policy.this.egress.network_access.policy_enforcement.enforcement_mode == "ENFORCED"
    )
    error_message = "network policy must restrict and enforce"
  }
  assert {
    condition     = length(databricks_mws_ncc_private_endpoint_rule.storage) == 1
    error_message = "one NCC private endpoint rule per storage account"
  }
  assert {
    condition     = databricks_workspace_conf.this[0].custom_config["enableExportNotebook"] == "false"
    error_message = "data-leak features must be configurable"
  }
}

run "ip_access_lists_and_logs" {
  command = apply

  variables {
    enable_ip_access_lists                = true
    allowed_ip_ranges                     = ["203.0.113.0/24", "198.51.100.10/32"]
    enable_diagnostic_settings            = true
    diagnostic_log_analytics_workspace_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.OperationalInsights/workspaces/law"
  }

  assert {
    condition     = length(databricks_ip_access_list.allowed) == 2
    error_message = "one allow list per range"
  }
  assert {
    condition     = databricks_workspace_conf.this[0].custom_config["enableIpAccessLists"] == "true"
    error_message = "IP access lists must be enabled in workspace config"
  }
  assert {
    condition     = length(module.monitoring) == 1
    error_message = "diagnostic settings must be created"
  }
}

run "rejects_bad_prefix" {
  command = plan

  variables {
    workspace_prefix = "Not-Valid"
  }

  expect_failures = [var.workspace_prefix]
}
