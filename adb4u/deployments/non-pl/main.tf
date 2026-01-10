***REMOVED*** ==============================================
***REMOVED*** Resource Group
***REMOVED*** ==============================================

***REMOVED*** Random suffix for unique resource naming
resource "random_string" "deployment_suffix" {
  length  = 4
  special = false
  upper   = false
  lower   = true
  numeric = true
}

locals {
  ***REMOVED*** Merge user-provided tags with required owner and keepuntil tags
  all_tags = merge(
    var.tags,
    {
      Owner     = var.tag_owner
      KeepUntil = var.tag_keepuntil
    }
  )
  
  ***REMOVED*** Add suffix to metastore name for uniqueness
  metastore_name_with_suffix = var.metastore_name != "" ? "${var.metastore_name}-${random_string.deployment_suffix.result}" : ""
}

resource "azurerm_resource_group" "this" {
  name     = var.resource_group_name
  location = var.location
  tags     = local.all_tags
}

***REMOVED*** ==============================================
***REMOVED*** Networking Module
***REMOVED*** ==============================================

module "networking" {
  source = "../../modules/networking"

  ***REMOVED*** BYOV or create new
  use_existing_network = var.use_existing_network

  ***REMOVED*** Existing network (BYOV)
  existing_vnet_name            = var.existing_vnet_name
  existing_resource_group_name  = var.existing_resource_group_name
  existing_public_subnet_name   = var.existing_public_subnet_name
  existing_private_subnet_name  = var.existing_private_subnet_name
  existing_nsg_name             = var.existing_nsg_name

  ***REMOVED*** New network configuration
  vnet_address_space            = var.vnet_address_space
  public_subnet_address_prefix  = var.public_subnet_address_prefix
  private_subnet_address_prefix = var.private_subnet_address_prefix

  ***REMOVED*** Non-PL pattern: NAT Gateway enabled, Private Link disabled
  enable_nat_gateway  = var.enable_nat_gateway
  enable_private_link = false

  ***REMOVED*** Core configuration
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  workspace_prefix    = var.workspace_prefix
  tags                = local.all_tags

  depends_on = [azurerm_resource_group.this]
}

***REMOVED*** ==============================================
***REMOVED*** Workspace Module
***REMOVED*** ==============================================

module "workspace" {
  source = "../../modules/workspace"

  ***REMOVED*** Workspace configuration
  workspace_name   = "${var.workspace_prefix}-workspace"
  workspace_prefix = var.workspace_prefix

  ***REMOVED*** Networking
  vnet_id                              = module.networking.vnet_id
  public_subnet_name                   = module.networking.subnet_names["public"]
  private_subnet_name                  = module.networking.subnet_names["private"]
  public_subnet_nsg_association_id     = module.networking.public_subnet_nsg_association_id
  private_subnet_nsg_association_id    = module.networking.private_subnet_nsg_association_id
  enable_private_link                  = false  ***REMOVED*** Non-PL pattern

  ***REMOVED*** Customer-Managed Keys (optional)
  enable_cmk_managed_services = var.enable_cmk_managed_services
  enable_cmk_managed_disks    = var.enable_cmk_managed_disks
  enable_cmk_dbfs_root        = var.enable_cmk_dbfs_root
  cmk_key_vault_key_id        = var.cmk_key_vault_key_id

  ***REMOVED*** IP Access Lists (optional)
  enable_ip_access_lists = var.enable_ip_access_lists
  allowed_ip_ranges      = var.allowed_ip_ranges

  ***REMOVED*** Core configuration
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = local.all_tags

  depends_on = [module.networking]
}

***REMOVED*** ==============================================
***REMOVED*** Unity Catalog Module
***REMOVED*** ==============================================

module "unity_catalog" {
  source = "../../modules/unity-catalog"

  providers = {
    databricks.account   = databricks.account
    databricks.workspace = databricks.workspace
  }

  ***REMOVED*** Metastore configuration
  create_metastore      = var.create_metastore
  existing_metastore_id = var.existing_metastore_id
  metastore_name        = local.metastore_name_with_suffix
  databricks_account_id = var.databricks_account_id

  ***REMOVED*** Workspace
  workspace_id     = module.workspace.workspace_id_numeric  ***REMOVED*** Numeric ID for Unity Catalog
  workspace_prefix = var.workspace_prefix

  ***REMOVED*** Storage configuration (Non-PL: Service Endpoints)
  create_metastore_storage        = var.create_metastore
  create_external_location_storage = true
  enable_private_link_storage      = false  ***REMOVED*** Use Service Endpoints (cost-efficient)
  service_endpoints_enabled        = true
  enable_service_endpoint_policies = true

  ***REMOVED*** Access Connector
  create_access_connector               = var.create_access_connector
  existing_access_connector_id          = var.existing_access_connector_id
  existing_access_connector_principal_id = var.existing_access_connector_principal_id

  ***REMOVED*** Core configuration
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = local.all_tags

  depends_on = [module.workspace]
}
