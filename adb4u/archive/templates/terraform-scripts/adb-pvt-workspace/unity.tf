***REMOVED*** Creates a Databricks access connector with a system-assigned managed identity for root storage.
***REMOVED*** This connector allows Databricks to interact with the storage account using managed identity permissions.
resource "azurerm_databricks_access_connector" "uc_root_mi" {
  name                = "${local.prefix}-uc-rootstorage-mi"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  identity {
    type = "SystemAssigned"
  }
}

***REMOVED*** Creates a highly available storage account with geo-redundant storage replication (GRS).
***REMOVED*** This storage account is used as the root storage for Unity Catalog in Databricks and has hierarchical namespace enabled.
resource "azurerm_storage_account" "uc_root_storage" {
  name                     = "${var.uc_root_storage}${random_string.naming.result}"
  resource_group_name      = azurerm_resource_group.this.name
  location                 = azurerm_resource_group.this.location
  tags                     = azurerm_resource_group.this.tags
  account_tier             = "Standard"
  account_replication_type = "GRS"
  is_hns_enabled           = true
}

***REMOVED*** Creates a private storage container within the root storage account for storing Unity Catalog data.
***REMOVED*** This container is accessible only through authorized Databricks instances.
resource "azurerm_storage_container" "uc_root_container" {
  name                  = "uc-root-container-${random_string.naming.result}"
  storage_account_name  = azurerm_storage_account.uc_root_storage.name
  container_access_type = "private"
}

***REMOVED*** Assigns the "Storage Blob Data Contributor" role to the managed identity of the Databricks access connector.
***REMOVED*** This allows Databricks to read and write to the root storage account container.
resource "azurerm_role_assignment" "uc_root_mi_role_assignment" {
  scope                = azurerm_storage_account.uc_root_storage.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_databricks_access_connector.uc_root_mi.identity[0].principal_id
}

***REMOVED*** Creates a Databricks metastore, which is required to manage Unity Catalog and enforce data governance policies.
***REMOVED*** The `storage_root` parameter specifies the root path in the storage account for metadata storage.
resource "databricks_metastore" "this" {
  provider = databricks.accounts
  name     = "primary-${random_string.naming.result}"
  storage_root = format("abfss://%s@%s.dfs.core.windows.net/",
    azurerm_storage_container.uc_root_container.name,
    azurerm_storage_account.uc_root_storage.name
  )
  force_destroy = true
  region        = azurerm_resource_group.this.location
}

***REMOVED*** Sets up a managed identity credential for the Unity Catalog root metastore,
***REMOVED*** allowing it to access the storage account for Unity Catalog metadata storage.
resource "databricks_metastore_data_access" "uc_root_credential" {
  provider     = databricks.accounts
  metastore_id = databricks_metastore.this.id
  name         = "uc-root-creds-${random_string.naming.result}"
  azure_managed_identity {
    access_connector_id = azurerm_databricks_access_connector.uc_root_mi.id
  }
  is_default = true
}

***REMOVED*** Assigns the metastore to a Databricks workspace and sets up the default catalog as "main".
resource "databricks_metastore_assignment" "this" {
  provider             = databricks.accounts
  workspace_id         = azurerm_databricks_workspace.this.workspace_id
  metastore_id         = databricks_metastore.this.id
  default_catalog_name = "main"

  depends_on = [
    azurerm_databricks_workspace.this
  ]
}

***REMOVED*** Creates another Databricks access connector with system-assigned managed identity
***REMOVED*** for accessing external storage for additional Unity Catalog data.
resource "azurerm_databricks_access_connector" "uc_ext_mi" {
  name                = "${local.prefix}-uc-extstorage-mi"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  identity {
    type = "SystemAssigned"
  }
}

***REMOVED*** Creates an additional storage account with geo-redundant storage replication for external storage.
***REMOVED*** This account will also be used by Unity Catalog for external data storage.
resource "azurerm_storage_account" "uc_ext_storage" {
  name                     = "${var.uc_ext_storage}${random_string.naming.result}"
  resource_group_name      = azurerm_resource_group.this.name
  location                 = azurerm_resource_group.this.location
  tags                     = azurerm_resource_group.this.tags
  account_tier             = "Standard"
  account_replication_type = "GRS"
  is_hns_enabled           = true
}

***REMOVED*** Creates a private storage container within the external storage account.
***REMOVED*** This container is intended to hold external data for Unity Catalog.
resource "azurerm_storage_container" "uc_ext_storage_container" {
  name                  = "uc-ext-container-${random_string.naming.result}"
  storage_account_name  = azurerm_storage_account.uc_ext_storage.name
  container_access_type = "private"
}

***REMOVED*** Assigns the "Storage Blob Data Contributor" role to the managed identity of the Databricks access connector for external storage.
resource "azurerm_role_assignment" "ext_storage_role" {
  scope                = azurerm_storage_account.uc_ext_storage.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_databricks_access_connector.uc_ext_mi.identity[0].principal_id
}

***REMOVED*** Creates a Databricks storage credential linked to the managed identity of the external storage access connector,
***REMOVED*** allowing Unity Catalog to securely access the external storage container.
resource "databricks_storage_credential" "uc_ext_credendtial1" {
  name = azurerm_databricks_access_connector.uc_ext_mi.name
  azure_managed_identity {
    access_connector_id = azurerm_databricks_access_connector.uc_ext_mi.id
  }
  comment = "Managed by TF"
  depends_on = [
    databricks_metastore_assignment.this
  ]
}

***REMOVED*** Defines an external storage location in Unity Catalog, pointing to the external storage container.
***REMOVED*** This location will allow Databricks to manage and access data stored outside the main storage account.
resource "databricks_external_location" "uc_ext_location1" {
  name           = "external"
  url            = format("abfss://%s@%s.dfs.core.windows.net",
                          azurerm_storage_container.uc_ext_storage_container.name,
                          azurerm_storage_account.uc_ext_storage.name)
  credential_name = databricks_storage_credential.uc_ext_credendtial1.name
  comment         = "ext location created and managed by terraform"
  depends_on      = [
    databricks_metastore_assignment.this
  ]
}

***REMOVED*** Grants all privileges to the specified admin user on the Unity Catalog metastore.
***REMOVED*** This enables the user to manage and access data within Unity Catalog.
resource "databricks_grants" "all_grants" {
  metastore = databricks_metastore.this.id
  grant {
    principal  = var.admin_user
    privileges = ["CREATE_CATALOG","CREATE_EXTERNAL_LOCATION","CREATE_RECIPIENT","CREATE_SHARE","CREATE_PROVIDER"]
  }
  depends_on = [
    databricks_metastore_assignment.this
  ]
}