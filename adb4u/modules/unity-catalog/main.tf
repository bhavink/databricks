# ==============================================
# Access Connector for Unity Catalog
# ==============================================

resource "azurerm_databricks_access_connector" "this" {
  count               = var.create_access_connector ? 1 : 0
  name                = local.access_connector_name
  resource_group_name = var.resource_group_name
  location            = var.location

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# ==============================================
# Metastore Root Storage Account
# ==============================================
# Unity Catalog Metastore Storage Account
# ==============================================
# ⚠️ IMPORTANT: Storage accounts containing Unity Catalog schemas/tables
# may require manual cleanup before destroy. Consider:
# - DROP SCHEMA cascade operations before terraform destroy
# - Backup critical data before destruction
# - Storage accounts will be destroyed even with data (no force_destroy needed)

resource "azurerm_storage_account" "metastore" {
  count                     = var.create_metastore_storage ? 1 : 0
  name                      = local.metastore_storage_name
  resource_group_name       = var.resource_group_name
  location                  = var.location
  account_tier              = "Standard"
  account_replication_type  = "LRS"
  is_hns_enabled            = true  # Hierarchical namespace for ADLS Gen2
  min_tls_version           = "TLS1_2"

  # Public network access control
  public_network_access_enabled = !var.enable_private_link_storage

  # Network rules - Allow by default for initial setup
  # Service Endpoint Policies will be configured separately for security
  network_rules {
    default_action = "Allow"
    bypass         = ["AzureServices"]
  }

  tags = var.tags
}

resource "azurerm_storage_container" "metastore" {
  count                 = var.create_metastore_storage ? 1 : 0
  name                  = local.metastore_container_name
  storage_account_name  = azurerm_storage_account.metastore[0].name
  container_access_type = "private"
}

# Grant Access Connector permissions to metastore storage
resource "azurerm_role_assignment" "metastore_contributor" {
  count                = var.create_metastore_storage ? 1 : 0
  scope                = azurerm_storage_account.metastore[0].id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = local.access_connector_principal_id
}

# ==============================================
# External Location Storage Account
# ==============================================

resource "azurerm_storage_account" "external" {
  count                     = var.create_external_location_storage ? 1 : 0
  name                      = local.external_storage_name
  resource_group_name       = var.resource_group_name
  location                  = var.location
  account_tier              = "Standard"
  account_replication_type  = "LRS"
  is_hns_enabled            = true  # Hierarchical namespace for ADLS Gen2
  min_tls_version           = "TLS1_2"

  # Public network access control
  public_network_access_enabled = !var.enable_private_link_storage

  # Network rules - Allow by default for initial setup
  # Service Endpoint Policies will be configured separately for security
  network_rules {
    default_action = "Allow"
    bypass         = ["AzureServices"]
  }

  tags = var.tags
}

resource "azurerm_storage_container" "external" {
  count                 = var.create_external_location_storage ? 1 : 0
  name                  = local.external_container_name
  storage_account_name  = azurerm_storage_account.external[0].name
  container_access_type = "private"
}

# Grant Access Connector permissions to external storage
resource "azurerm_role_assignment" "external_contributor" {
  count                = var.create_external_location_storage ? 1 : 0
  scope                = azurerm_storage_account.external[0].id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = local.access_connector_principal_id
}

# ==============================================
# Private Endpoints for Storage (if enabled)
# ==============================================

# Metastore Storage Private Endpoints
resource "azurerm_private_endpoint" "metastore_blob" {
  count               = var.create_metastore_storage && var.enable_private_link_storage ? 1 : 0
  name                = local.metastore_storage_pe_name_blob
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.storage_private_endpoint_subnet_id

  private_service_connection {
    name                           = "${local.metastore_storage_pe_name_blob}-connection"
    private_connection_resource_id = azurerm_storage_account.metastore[0].id
    is_manual_connection           = false
    subresource_names              = ["blob"]
  }

  tags = var.tags
}

resource "azurerm_private_endpoint" "metastore_dfs" {
  count               = var.create_metastore_storage && var.enable_private_link_storage ? 1 : 0
  name                = local.metastore_storage_pe_name_dfs
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.storage_private_endpoint_subnet_id

  private_service_connection {
    name                           = "${local.metastore_storage_pe_name_dfs}-connection"
    private_connection_resource_id = azurerm_storage_account.metastore[0].id
    is_manual_connection           = false
    subresource_names              = ["dfs"]
  }

  tags = var.tags
}

# External Storage Private Endpoints
resource "azurerm_private_endpoint" "external_blob" {
  count               = var.create_external_location_storage && var.enable_private_link_storage ? 1 : 0
  name                = local.external_storage_pe_name_blob
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.storage_private_endpoint_subnet_id

  private_service_connection {
    name                           = "${local.external_storage_pe_name_blob}-connection"
    private_connection_resource_id = azurerm_storage_account.external[0].id
    is_manual_connection           = false
    subresource_names              = ["blob"]
  }

  tags = var.tags
}

resource "azurerm_private_endpoint" "external_dfs" {
  count               = var.create_external_location_storage && var.enable_private_link_storage ? 1 : 0
  name                = local.external_storage_pe_name_dfs
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.storage_private_endpoint_subnet_id

  private_service_connection {
    name                           = "${local.external_storage_pe_name_dfs}-connection"
    private_connection_resource_id = azurerm_storage_account.external[0].id
    is_manual_connection           = false
    subresource_names              = ["dfs"]
  }

  tags = var.tags
}

# ==============================================
# Unity Catalog Metastore
# ==============================================
# Metastore is an account-level resource
# Must use the account provider

resource "databricks_metastore" "this" {
  provider = databricks.account
  
  count = var.create_metastore ? 1 : 0
  name  = var.metastore_name != "" ? var.metastore_name : "${var.workspace_prefix}-metastore-${var.location}"
  
  storage_root = "abfss://${azurerm_storage_container.metastore[0].name}@${azurerm_storage_account.metastore[0].name}.dfs.core.windows.net/"
  
  region        = var.location
  force_destroy = true  # CRITICAL: Must be true to allow clean destroy of metastore with root credential
  
  # IMPORTANT: Do not add lifecycle.ignore_changes for force_destroy
  # It will prevent clean destroy when you need to tear down resources

  depends_on = [
    azurerm_role_assignment.metastore_contributor
  ]
}

# Metastore Data Access Configuration
# Account-level resource
resource "databricks_metastore_data_access" "this" {
  provider = databricks.account
  
  count        = var.create_metastore ? 1 : 0
  metastore_id = databricks_metastore.this[0].id
  name         = "${var.workspace_prefix}-metastore-access"
  
  azure_managed_identity {
    access_connector_id = local.access_connector_id
  }

  is_default = true

  depends_on = [
    azurerm_role_assignment.metastore_contributor
  ]
}

# Attach Workspace to Metastore
# Account-level resource
resource "databricks_metastore_assignment" "this" {
  provider = databricks.account
  
  metastore_id = local.metastore_id
  workspace_id = var.workspace_id

  depends_on = [
    databricks_metastore.this,
    databricks_metastore_data_access.this
  ]
}

# ==============================================
# Storage Credential for External Locations
# ==============================================
# Storage credentials are workspace-level resources
# Must use the workspace provider (not account provider)

resource "databricks_storage_credential" "external" {
  provider = databricks.workspace
  
  count = var.create_external_location_storage ? 1 : 0
  name  = "${var.workspace_prefix}-external-credential"
  
  azure_managed_identity {
    access_connector_id = local.access_connector_id
  }

  depends_on = [
    databricks_metastore_assignment.this,
    azurerm_role_assignment.external_contributor
  ]
}

# ==============================================
# External Location
# ==============================================
# External locations are workspace-level resources
# Must use the workspace provider (not account provider)

resource "databricks_external_location" "this" {
  provider = databricks.workspace
  
  count           = var.create_external_location_storage ? 1 : 0
  name            = local.external_location_name
  url             = "abfss://${azurerm_storage_container.external[0].name}@${azurerm_storage_account.external[0].name}.dfs.core.windows.net/"
  credential_name = databricks_storage_credential.external[0].name

  depends_on = [
    databricks_storage_credential.external
  ]
}
