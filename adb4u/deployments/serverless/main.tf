# ==============================================
# Serverless Azure Databricks Workspace
# ==============================================
# The workspace is created by the official Databricks Security Reference
# Architecture module (serverless_workspace), pinned to a reviewed commit.
# This root adds what the module expects as inputs (resource group, private
# endpoint network, DNS zone, NCC, network policy) plus the optional
# front-end private endpoint, IP access lists and diagnostic logs.
#
# Module: https://github.com/databricks/terraform-databricks-sra/tree/main/azure/tf/modules/serverless_workspace
# Docs:   https://learn.microsoft.com/en-us/azure/databricks/admin/workspace/serverless-workspaces

locals {
  tags = merge({ ManagedBy = "Terraform", Pattern = "Serverless" }, var.tags)
}

data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "this" {
  name     = var.resource_group_name
  location = var.location
  tags     = local.tags
}

# ==============================================
# Private endpoint network
# ==============================================

resource "azurerm_virtual_network" "this" {
  name                = "${var.workspace_prefix}-vnet"
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  address_space       = var.vnet_address_space
  tags                = local.tags
}

resource "azurerm_subnet" "privatelink" {
  name                 = "${var.workspace_prefix}-privatelink-subnet"
  resource_group_name  = azurerm_resource_group.this.name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = var.privatelink_subnet_address_prefix
}

resource "azurerm_private_dns_zone" "databricks" {
  name                = "privatelink.azuredatabricks.net"
  resource_group_name = azurerm_resource_group.this.name
  tags                = local.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "databricks" {
  name                  = "${var.workspace_prefix}-databricks-dns-link"
  resource_group_name   = azurerm_resource_group.this.name
  private_dns_zone_name = azurerm_private_dns_zone.databricks.name
  virtual_network_id    = azurerm_virtual_network.this.id
  tags                  = local.tags
}

# ==============================================
# Serverless connectivity (account level)
# ==============================================

resource "databricks_mws_network_connectivity_config" "this" {
  name   = "${var.workspace_prefix}-ncc"
  region = var.location
}

resource "databricks_account_network_policy" "this" {
  network_policy_id = "${var.workspace_prefix}-serverless"
  account_id        = var.databricks_account_id

  egress = {
    network_access = {
      restriction_mode = var.enable_network_policy ? "RESTRICTED_ACCESS" : "FULL_ACCESS"
      allowed_internet_destinations = var.enable_network_policy ? [
        for d in var.serverless_allowed_internet_destinations : {
          destination               = d
          internet_destination_type = "DNS_NAME"
        }
      ] : []
      allowed_storage_destinations = var.enable_network_policy ? [
        for a in var.serverless_allowed_storage_accounts : {
          azure_storage_account    = a
          azure_storage_service    = "dfs"
          storage_destination_type = "AZURE_STORAGE"
        }
      ] : []
      policy_enforcement = {
        enforcement_mode = var.network_policy_enforcement_mode
      }
    }
  }
}

# Private endpoints from serverless compute to customer storage. Azure
# creates them pending; approve each on the storage account (outside Terraform).
resource "databricks_mws_ncc_private_endpoint_rule" "storage" {
  for_each = toset(var.serverless_private_endpoint_storage_account_ids)

  network_connectivity_config_id = databricks_mws_network_connectivity_config.this.network_connectivity_config_id
  resource_id                    = each.value
  group_id                       = "dfs"
}

# ==============================================
# Workspace (official SRA module)
# ==============================================

module "workspace" {
  # Pinned to a reviewed SRA commit; bump deliberately (CI validates and tests this root).
  source = "git::https://github.com/databricks/terraform-databricks-sra.git//azure/tf/modules/serverless_workspace?ref=bc5af72e46e9ddcf21b7eb246b4e4bad0e3d3be4"

  resource_group_name = azurerm_resource_group.this.name
  location            = var.location
  resource_suffix     = var.workspace_prefix
  tags                = local.tags
  name_overrides = {
    databricks_workspace = "${var.workspace_prefix}-workspace"
    private_endpoint     = "${var.workspace_prefix}-pe"
  }

  provisioner_principal_id   = data.azurerm_client_config.current.object_id
  private_endpoint_subnet_id = azurerm_subnet.privatelink.id
  dns_zone_ids = {
    backend = azurerm_private_dns_zone.databricks.id
    dfs     = null
    blob    = null
  }

  metastore_id      = var.metastore_id
  ncc_id            = databricks_mws_network_connectivity_config.this.network_connectivity_config_id
  network_policy_id = databricks_account_network_policy.this.network_policy_id

  is_frontend_private_link_enabled = !var.enable_public_network_access
  is_kms_enabled                   = var.managed_services_cmk_key_id != null
  managed_services_key_id          = var.managed_services_cmk_key_id

  depends_on = [azurerm_private_dns_zone_virtual_network_link.databricks]
}

# Front-end (UI/API) private endpoint: required to reach the workspace when
# public network access is disabled.
resource "azurerm_private_endpoint" "ui_api" {
  count = var.enable_public_network_access ? 0 : 1

  name                = "${var.workspace_prefix}-pe-ui-api"
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  subnet_id           = azurerm_subnet.privatelink.id

  private_service_connection {
    name                           = "${var.workspace_prefix}-psc-ui-api"
    private_connection_resource_id = module.workspace.id
    is_manual_connection           = false
    subresource_names              = ["databricks_ui_api"]
  }

  private_dns_zone_group {
    name                 = "private-dns-zone-ui-api"
    private_dns_zone_ids = [azurerm_private_dns_zone.databricks.id]
  }

  tags = local.tags
}

# ==============================================
# Workspace settings (optional)
# ==============================================

resource "databricks_workspace_conf" "this" {
  count    = var.enable_ip_access_lists || length(var.additional_workspace_config) > 0 ? 1 : 0
  provider = databricks.workspace

  custom_config = merge(
    { "enableIpAccessLists" = var.enable_ip_access_lists ? "true" : "false" },
    var.additional_workspace_config
  )
}

resource "databricks_ip_access_list" "allowed" {
  count    = var.enable_ip_access_lists ? length(var.allowed_ip_ranges) : 0
  provider = databricks.workspace

  list_type    = "ALLOW"
  ip_addresses = [var.allowed_ip_ranges[count.index]]
  label        = "Allowed IP range ${count.index + 1}"
  enabled      = true

  depends_on = [databricks_workspace_conf.this]
}

# ==============================================
# Diagnostic logs (optional)
# ==============================================

module "monitoring" {
  count  = var.enable_diagnostic_settings ? 1 : 0
  source = "../../modules/monitoring"

  workspace_id                   = module.workspace.id
  log_analytics_workspace_id     = var.diagnostic_log_analytics_workspace_id
  storage_account_id             = var.diagnostic_storage_account_id
  eventhub_authorization_rule_id = var.diagnostic_eventhub_authorization_rule_id
  eventhub_name                  = var.diagnostic_eventhub_name
}
