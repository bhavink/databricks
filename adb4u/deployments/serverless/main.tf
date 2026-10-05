# ==============================================
# Serverless Azure Databricks Workspace
# ==============================================
# Serverless compute runs in the Databricks account, so the workspace needs
# no VNet: a resource group, the workspace, and account-level connectivity
# (NCC + network policy). A network is created only for a private front-end
# (enable_public_network_access = false), which needs private endpoints.
#
# The workspace is created with the same ARM call as the official Databricks
# SRA serverless_workspace module (Microsoft.Databricks/workspaces with
# computeMode = "Serverless", via AzAPI), without the module's always-on
# browser-authentication private endpoint and the VNet it requires.
# azurerm_databricks_workspace cannot set computeMode yet
# (https://github.com/hashicorp/terraform-provider-azurerm/issues/31218).
#
# Reference: https://github.com/databricks/terraform-databricks-sra/tree/main/azure/tf/modules/serverless_workspace
# Docs:      https://learn.microsoft.com/en-us/azure/databricks/admin/workspace/serverless-workspaces

locals {
  tags            = merge({ ManagedBy = "Terraform", Pattern = "Serverless" }, var.tags)
  private_network = var.enable_public_network_access ? 0 : 1

  # Key Vault key URI (https://<vault>.vault.azure.net/keys/<name>/<version>) -> ARM encryption fields
  cmk = var.managed_services_cmk_key_id == null ? null : regex(
    "^(?P<vault_uri>https://[^/]+/)keys/(?P<name>[^/]+)/(?P<version>[^/]+)$", var.managed_services_cmk_key_id
  )
}

data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "this" {
  name     = var.resource_group_name
  location = var.location
  tags     = local.tags
}

# ==============================================
# Workspace
# ==============================================

resource "azapi_resource" "workspace" {
  type      = "Microsoft.Databricks/workspaces@2026-01-01"
  name      = "${var.workspace_prefix}-workspace"
  parent_id = azurerm_resource_group.this.id
  location  = var.location
  tags      = local.tags

  body = {
    sku = { name = "premium" }
    properties = {
      # Serverless-only: the API rejects classic clusters. VNet injection,
      # managed resource group, managed-disk CMK and NSG rules do not apply.
      computeMode         = "Serverless"
      publicNetworkAccess = var.enable_public_network_access ? "Enabled" : "Disabled"
      encryption = local.cmk == null ? null : {
        entities = {
          managedServices = {
            keySource = "Microsoft.Keyvault"
            keyVaultProperties = {
              keyName     = local.cmk.name
              keyVaultUri = local.cmk.vault_uri
              keyVersion  = local.cmk.version
            }
          }
        }
      }
    }
  }

  ignore_null_property   = true
  response_export_values = ["properties.workspaceUrl", "properties.workspaceId"]
}

locals {
  workspace_id  = azapi_resource.workspace.output.properties.workspaceId
  workspace_url = azapi_resource.workspace.output.properties.workspaceUrl
}

# Workspace admin for whoever runs Terraform, so the workspace provider can
# authenticate with the same identity (as the official module does).
resource "azurerm_role_assignment" "provisioner" {
  scope                = azapi_resource.workspace.id
  role_definition_name = "Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

# ==============================================
# Account level: Unity Catalog and serverless connectivity
# ==============================================

resource "databricks_metastore_assignment" "this" {
  workspace_id = local.workspace_id
  metastore_id = var.metastore_id
}

resource "databricks_mws_network_connectivity_config" "this" {
  name   = "${var.workspace_prefix}-ncc"
  region = var.location
}

resource "databricks_mws_ncc_binding" "this" {
  network_connectivity_config_id = databricks_mws_network_connectivity_config.this.network_connectivity_config_id
  workspace_id                   = local.workspace_id
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

resource "databricks_workspace_network_option" "this" {
  workspace_id      = local.workspace_id
  network_policy_id = databricks_account_network_policy.this.network_policy_id
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
# Private front-end (only when public access is disabled)
# ==============================================
# Users reach the workspace through private endpoints in this VNet; peer it
# or connect it to the network your users are on.

resource "azurerm_virtual_network" "this" {
  count               = local.private_network
  name                = "${var.workspace_prefix}-vnet"
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  address_space       = var.vnet_address_space
  tags                = local.tags
}

resource "azurerm_subnet" "privatelink" {
  count                = local.private_network
  name                 = "${var.workspace_prefix}-privatelink-subnet"
  resource_group_name  = azurerm_resource_group.this.name
  virtual_network_name = azurerm_virtual_network.this[0].name
  address_prefixes     = var.privatelink_subnet_address_prefix
}

resource "azurerm_private_dns_zone" "databricks" {
  count               = local.private_network
  name                = "privatelink.azuredatabricks.net"
  resource_group_name = azurerm_resource_group.this.name
  tags                = local.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "databricks" {
  count                 = local.private_network
  name                  = "${var.workspace_prefix}-databricks-dns-link"
  resource_group_name   = azurerm_resource_group.this.name
  private_dns_zone_name = azurerm_private_dns_zone.databricks[0].name
  virtual_network_id    = azurerm_virtual_network.this[0].id
  tags                  = local.tags
}

# UI/API and browser authentication (SSO) endpoints.
resource "azurerm_private_endpoint" "frontend" {
  for_each = local.private_network == 1 ? toset(["databricks_ui_api", "browser_authentication"]) : toset([])

  name                = "${var.workspace_prefix}-pe-${replace(each.key, "_", "-")}"
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  subnet_id           = azurerm_subnet.privatelink[0].id

  private_service_connection {
    name                           = "${var.workspace_prefix}-psc-${replace(each.key, "_", "-")}"
    private_connection_resource_id = azapi_resource.workspace.id
    is_manual_connection           = false
    subresource_names              = [each.key]
  }

  private_dns_zone_group {
    name                 = "private-dns-zone"
    private_dns_zone_ids = [azurerm_private_dns_zone.databricks[0].id]
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

  depends_on = [azurerm_role_assignment.provisioner, databricks_metastore_assignment.this]
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

  workspace_id                   = azapi_resource.workspace.id
  log_analytics_workspace_id     = var.diagnostic_log_analytics_workspace_id
  storage_account_id             = var.diagnostic_storage_account_id
  eventhub_authorization_rule_id = var.diagnostic_eventhub_authorization_rule_id
  eventhub_name                  = var.diagnostic_eventhub_name
}
