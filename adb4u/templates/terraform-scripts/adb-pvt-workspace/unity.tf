resource "azurerm_databricks_access_connector" "unity" {
  name                = "${local.prefix}-ucroot-storage-mi-${random_string.naming.result}"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_storage_account" "uc_root_storage" {
  name                     = "${var.uc_root_storage}${random_string.naming.result}"
  resource_group_name      = azurerm_resource_group.this.name
  location                 = azurerm_resource_group.this.location
  tags                     = azurerm_resource_group.this.tags
  account_tier             = "Standard"
  account_replication_type = "GRS"
  is_hns_enabled           = true
}

resource "azurerm_storage_container" "unity_catalog" {
  name                  = "uc-root-container-${random_string.naming.result}"
  storage_account_name  = azurerm_storage_account.uc_root_storage.name
  container_access_type = "private"
}

resource "azurerm_role_assignment" "adb_ws" {
  scope                = azurerm_storage_account.uc_root_storage.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_databricks_access_connector.unity.identity[0].principal_id
}

resource "databricks_metastore" "this" {
  provider = databricks.accounts
  name     = "primary-${random_string.naming.result}"
  storage_root = format("abfss://%s@%s.dfs.core.windows.net/",
    azurerm_storage_container.unity_catalog.name,
  azurerm_storage_account.uc_root_storage.name)
  force_destroy = true
  region        = azurerm_resource_group.this.location
}

resource "databricks_metastore_data_access" "first" {
  provider     = databricks.accounts
  metastore_id = databricks_metastore.this.id
  name         = "uc-root-creds-${random_string.naming.result}"
  azure_managed_identity {
    access_connector_id = azurerm_databricks_access_connector.unity.id
  }

  is_default = true
}

resource "databricks_metastore_assignment" "this" {
  provider             = databricks.accounts
  workspace_id         = azurerm_databricks_workspace.this.workspace_id
  metastore_id         = databricks_metastore.this.id
  default_catalog_name = "main"

  depends_on = [
    azurerm_databricks_workspace.this
  ]
}

// external storage and credentials configurations



resource "azurerm_databricks_access_connector" "ext_access_connector" {
  name                = "${local.prefix}-uc-extstorage-mi-${random_string.naming.result}"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  identity {
    type = "SystemAssigned"
  }
}


resource "azurerm_storage_account" "uc_ext_storage" {
  name                     = "${var.uc_ext_storage}${random_string.naming.result}"
  resource_group_name      = azurerm_resource_group.this.name
  location                 = azurerm_resource_group.this.location
  tags                     = azurerm_resource_group.this.tags
  account_tier             = "Standard"
  account_replication_type = "GRS"
  is_hns_enabled           = true
}

resource "azurerm_storage_container" "ext_storage_container" {
  name                  = "uc-ext-container-${random_string.naming.result}"
  storage_account_name  = azurerm_storage_account.uc_ext_storage.name
  container_access_type = "private"
}

resource "azurerm_role_assignment" "ext_storage_role" {
  scope                = azurerm_storage_account.uc_ext_storage.id
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
    azurerm_storage_container.ext_storage_container.name,
  azurerm_storage_account.uc_ext_storage.name)

  credential_name = databricks_storage_credential.external.id
  comment         = "Managed by TF"
  depends_on = [
    databricks_metastore_assignment.this
  ]
}

resource "databricks_grants" "some" {
  external_location = databricks_external_location.some.id
  grant {
    principal  = "admins"
    privileges = ["CREATE_EXTERNAL_TABLE", "READ_FILES"]
  }
}


// grant permission to user on external storage and credentials

resource "databricks_grants" "all_grants" {
  metastore = databricks_metastore.this.id
  grant {
    principal  = var.admin_user
    privileges = ["CREATE_CATALOG","CREATE_EXTERNAL_LOCATION","CREATE_STORAGE_CREDENTIAL"]
  }
  depends_on = [
    databricks_metastore_assignment.this
  ]
}

