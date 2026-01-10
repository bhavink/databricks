# locals {
# #   resource_regex            = "(?i)subscriptions/(.+)/resourceGroups/(.+)/providers/Microsoft.Databricks/workspaces/(.+)"
#   subscription_id           = var.subscription_id
#   resource_group            = azurerm_resource_group.adb_rg.name
#   databricks_workspace_name = azurerm_databricks_workspace.adb_ws.name
#   tenant_id                 = data.azurerm_client_config.current.tenant_id
#   databricks_workspace_host = azurerm_databricks_workspace.adb_ws.workspace_url
#   databricks_workspace_id   = azurerm_databricks_workspace.adb_ws.workspace_id
#   prefix                    = replace(replace(lower(azurerm_resource_group.adb_rg.name), "rg", ""), "-", "")
# }

data "azurerm_client_config" "current" {
}


resource "azurerm_databricks_access_connector" "unity" {
  name                = "${var.prefix}-databricks-mi-${random_string.databricks_suffix.result}"
  resource_group_name = azurerm_resource_group.adb_rg.name
  location            = azurerm_resource_group.adb_rg.location
  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_storage_account" "unity_catalog" {
  name                     = "bkstorageroot"
  resource_group_name      = azurerm_resource_group.adb_rg.name
  location                 = azurerm_resource_group.adb_rg.location
  tags                     = azurerm_resource_group.adb_rg.tags
  account_tier             = "Standard"
  account_replication_type = "GRS"
  is_hns_enabled           = true
}

resource "azurerm_storage_container" "unity_catalog" {
  name                  = "bk-container-${random_string.databricks_suffix.result}"
  storage_account_name  = azurerm_storage_account.unity_catalog.name
  container_access_type = "private"
}

resource "azurerm_role_assignment" "adb_ws" {
  scope                = azurerm_storage_account.unity_catalog.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_databricks_access_connector.unity.identity[0].principal_id
}

resource "databricks_metastore" "this" {
  provider = databricks.accounts
  name     = "primary-${random_string.databricks_suffix.result}"
  storage_root = format("abfss://%s@%s.dfs.core.windows.net/",
    azurerm_storage_container.unity_catalog.name,
  azurerm_storage_account.unity_catalog.name)
  force_destroy = true
  region        = azurerm_resource_group.adb_rg.location
}

resource "databricks_metastore_data_access" "first" {
  provider     = databricks.accounts
  metastore_id = databricks_metastore.this.id
  name         = "uc-primary-storage-keys-${random_string.databricks_suffix.result}"
  azure_managed_identity {
    access_connector_id = azurerm_databricks_access_connector.unity.id
  }

  is_default = true
}

resource "databricks_metastore_assignment" "this" {
  provider             = databricks.accounts
  workspace_id         = azurerm_databricks_workspace.adb_ws.workspace_id
  metastore_id         = databricks_metastore.this.id
  default_catalog_name = "hive_metastore"

  depends_on = [
    azurerm_databricks_workspace.adb_ws
  ]
}

// external storage and credentials configurations



resource "azurerm_databricks_access_connector" "ext_access_connector" {
  name                = "ext-databricks-mi"
  resource_group_name = azurerm_resource_group.adb_rg.name
  location            = azurerm_resource_group.adb_rg.location
  identity {
    type = "SystemAssigned"
  }
}


resource "azurerm_storage_account" "ext_storage" {
  name                     = "bkextstorage"
  resource_group_name      = azurerm_resource_group.adb_rg.name
  location                 = azurerm_resource_group.adb_rg.location
  tags                     = azurerm_resource_group.adb_rg.tags
  account_tier             = "Standard"
  account_replication_type = "GRS"
  is_hns_enabled           = true
}

resource "azurerm_storage_container" "ext_storage" {
  name                  = "bk-ext"
  storage_account_name  = azurerm_storage_account.ext_storage.name
  container_access_type = "private"
}

resource "azurerm_role_assignment" "ext_storage" {
  scope                = azurerm_storage_account.ext_storage.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_databricks_access_connector.ext_access_connector.identity[0].principal_id
}


// create the databricks_storage_credential and databricks_external_location in Unity Catalog.

resource "databricks_storage_credential" "external" {
  name = azurerm_databricks_access_connector.ext_access_connector.name
  azure_managed_identity {
    access_connector_id = azurerm_databricks_access_connector.ext_access_connector.id
  }
  comment = "Managed by TF"
  depends_on = [
    databricks_metastore_assignment.this
  ]
}

resource "databricks_grants" "external_creds" {
  storage_credential = databricks_storage_credential.external.id
  grant {
    principal  = "Data Engineers"
    privileges = ["CREATE_EXTERNAL_TABLE"]
  }
}

resource "databricks_external_location" "some" {
  name = "external"
  url = format("abfss://%s@%s.dfs.core.windows.net",
    azurerm_storage_container.ext_storage.name,
  azurerm_storage_account.ext_storage.name)

  credential_name = databricks_storage_credential.external.id
  comment         = "Managed by TF"
  depends_on = [
    databricks_metastore_assignment.this
  ]
}

resource "databricks_grants" "some" {
  external_location = databricks_external_location.some.id
  grant {
    principal  = "Data Engineers"
    privileges = ["CREATE_EXTERNAL_TABLE", "READ_FILES"]
  }
}


// grant permission to user on external storage and credentials

resource "databricks_grants" "all_grants" {
  metastore = databricks_metastore.this.id
  grant {
    principal  = var.adb_ws_user1
    privileges = ["CREATE_CATALOG","CREATE_EXTERNAL_LOCATION","CREATE_STORAGE_CREDENTIAL"]
  }
  # grant {
  #   principal  = var.adb_ws_user2
  #   privileges = ["USE_CONNECTION","CREATE_EXTERNAL_LOCATION","CREATE_STORAGE_CREDENTIAL"]
  # }
  depends_on = [
    databricks_metastore_assignment.this
  ]
}

