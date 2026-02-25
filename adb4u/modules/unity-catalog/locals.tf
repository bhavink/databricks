# Random suffix for unique resource names
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# ==============================================
# Local Values
# ==============================================

locals {
  # Metastore configuration
  metastore_id = var.create_metastore ? databricks_metastore.this[0].id : var.existing_metastore_id

  # Resource naming with optional custom prefixes
  metastore_storage_name = replace(
    var.metastore_storage_name_prefix != "" ? "${var.metastore_storage_name_prefix}${random_string.suffix.result}" : "${var.workspace_prefix}metastore${random_string.suffix.result}",
    "-", ""
  )
  external_storage_name = replace(
    var.external_storage_name_prefix != "" ? "${var.external_storage_name_prefix}${random_string.suffix.result}" : "${var.workspace_prefix}external${random_string.suffix.result}",
    "-", ""
  )
  access_connector_name    = "${var.workspace_prefix}-uc-connector-${random_string.suffix.result}"
  metastore_container_name = "metastore"
  external_container_name  = "data"

  # External location name
  external_location_name = var.external_location_name != "" ? var.external_location_name : "${var.workspace_prefix}-external"

  # Access Connector references
  access_connector_id           = var.create_access_connector ? azurerm_databricks_access_connector.this[0].id : var.existing_access_connector_id
  access_connector_principal_id = var.create_access_connector ? azurerm_databricks_access_connector.this[0].identity[0].principal_id : var.existing_access_connector_principal_id

  # Storage connectivity strategy
  using_private_link      = var.enable_private_link_storage
  using_service_endpoints = var.service_endpoints_enabled && !var.enable_private_link_storage

  # Private endpoint names
  metastore_storage_pe_name_blob = "${local.metastore_storage_name}-pe-blob"
  metastore_storage_pe_name_dfs  = "${local.metastore_storage_name}-pe-dfs"
  external_storage_pe_name_blob  = "${local.external_storage_name}-pe-blob"
  external_storage_pe_name_dfs   = "${local.external_storage_name}-pe-dfs"
}
