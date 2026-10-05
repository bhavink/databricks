# Credential-free tests (mock provider): terraform init && terraform test

mock_provider "azurerm" {}
mock_provider "databricks" {}

variables {
  workspace_name                    = "test-workspace"
  workspace_prefix                  = "test"
  resource_group_name               = "rg-test"
  location                          = "eastus2"
  vnet_id                           = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Network/virtualNetworks/vnet"
  public_subnet_name                = "public"
  private_subnet_name               = "private"
  public_subnet_nsg_association_id  = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Network/virtualNetworks/vnet/subnets/public"
  private_subnet_nsg_association_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Network/virtualNetworks/vnet/subnets/private"
  databricks_account_id             = "00000000-0000-0000-0000-000000000000"
}

run "default_leaves_storage_firewall_off" {
  command = plan

  variables {
    enable_private_link = true
  }

  assert {
    condition     = azurerm_databricks_workspace.this.default_storage_firewall_enabled != true
    error_message = "storage firewall must be opt-in"
  }
  assert {
    condition     = length(azurerm_databricks_access_connector.storage_firewall) == 0
    error_message = "no access connector should be created by default"
  }
}

run "enabled_firewall_gets_dedicated_access_connector" {
  command = plan

  variables {
    enable_private_link             = true
    enable_default_storage_firewall = true
  }

  assert {
    condition     = azurerm_databricks_workspace.this.default_storage_firewall_enabled == true
    error_message = "storage firewall not enabled"
  }
  assert {
    condition     = length(azurerm_databricks_access_connector.storage_firewall) == 1
    error_message = "a dedicated access connector (outside the managed RG) is required"
  }
}

run "existing_access_connector_is_reused" {
  command = plan

  variables {
    enable_private_link                  = true
    enable_default_storage_firewall      = true
    storage_firewall_access_connector_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Databricks/accessConnectors/existing"
  }

  assert {
    condition     = length(azurerm_databricks_access_connector.storage_firewall) == 0
    error_message = "must not create a connector when one is supplied"
  }
  assert {
    condition     = azurerm_databricks_workspace.this.access_connector_id == var.storage_firewall_access_connector_id
    error_message = "supplied connector not used"
  }
}

run "firewall_without_private_link_is_rejected" {
  command = plan

  variables {
    enable_private_link             = false
    enable_default_storage_firewall = true
  }

  expect_failures = [azurerm_databricks_workspace.this]
}
