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
  
  ***REMOVED*** Determine if any CMK feature is enabled
  cmk_enabled = var.enable_cmk_managed_services || var.enable_cmk_managed_disks || var.enable_cmk_dbfs_root
  
  ***REMOVED*** ==============================================
  ***REMOVED*** BYOR Derived Flags (Master Control Logic)
  ***REMOVED*** ==============================================
  ***REMOVED*** When use_byor_infrastructure=true, automatically derive correct flags
  ***REMOVED*** to prevent user configuration errors.
  
  ***REMOVED*** Network: Use BYOR network if use_byor_infrastructure is true
  use_existing_network = var.use_byor_infrastructure ? true : var.use_existing_network
  
  ***REMOVED*** NAT Gateway: BYOR already created it, so disable workspace creation
  enable_nat_gateway = var.use_byor_infrastructure ? false : var.enable_nat_gateway
  
  ***REMOVED*** CMK Key Vault: BYOR already created it (if CMK enabled), so use existing
  create_key_vault = (var.use_byor_infrastructure && local.cmk_enabled) ? false : var.create_key_vault
}

***REMOVED*** ==============================================
***REMOVED*** Resource Group
***REMOVED*** ==============================================

***REMOVED*** Create new Resource Group only when not using BYOR
resource "azurerm_resource_group" "this" {
  count    = var.use_byor_infrastructure ? 0 : 1
  name     = var.resource_group_name
  location = var.location
  tags     = local.all_tags
  
  ***REMOVED*** Validation: When using BYOR, ensure network resources are provided
  lifecycle {
    precondition {
      condition = (
        var.use_byor_infrastructure == false ||
        (var.existing_vnet_name != "" && 
         var.existing_resource_group_name != "" &&
         var.existing_public_subnet_name != "" &&
         var.existing_private_subnet_name != "" &&
         var.existing_nsg_name != "")
      )
      error_message = <<-EOT
        When use_byor_infrastructure=true, all existing network resources must be provided:
        - existing_vnet_name
        - existing_resource_group_name
        - existing_public_subnet_name
        - existing_private_subnet_name
        - existing_nsg_name
      EOT
    }
    
    precondition {
      condition = (
        var.use_byor_infrastructure == false ||
        !local.cmk_enabled ||
        (var.existing_key_vault_id != "" && var.existing_key_id != "")
      )
      error_message = <<-EOT
        When use_byor_infrastructure=true with CMK enabled, Key Vault resources must be provided:
        - existing_key_vault_id
        - existing_key_id
      EOT
    }
  }
}

***REMOVED*** Local to use either existing or newly created RG name
locals {
  ***REMOVED*** When using BYOR, RG already exists - just use the variable
  ***REMOVED*** When not using BYOR, use the newly created RG name
  resource_group_name = var.use_byor_infrastructure ? var.resource_group_name : azurerm_resource_group.this[0].name
}

***REMOVED*** ==============================================
***REMOVED*** Key Vault Module (Optional - for CMK)
***REMOVED*** ==============================================

***REMOVED*** Only invoke key_vault module if creating a new Key Vault
module "key_vault" {
  count  = local.cmk_enabled && local.create_key_vault ? 1 : 0
  source = "../../modules/key-vault"

  ***REMOVED*** Create or use existing Key Vault
  create_key_vault      = local.create_key_vault
  existing_key_vault_id = var.existing_key_vault_id
  existing_key_id       = var.existing_key_id

  ***REMOVED*** Resource configuration
  workspace_prefix    = var.workspace_prefix
  resource_group_name = local.resource_group_name
  location            = var.location

  ***REMOVED*** Key configuration (auto-rotation enabled)
  key_name              = "databricks-cmk"
  enable_auto_rotation  = true
  rotation_policy_days  = 90

  ***REMOVED*** Security configuration
  enable_purge_protection = true
  soft_delete_retention_days = 90

  tags = local.all_tags

  depends_on = [azurerm_resource_group.this]
}

***REMOVED*** ==============================================
***REMOVED*** Networking Module
***REMOVED*** ==============================================

module "networking" {
  source = "../../modules/networking"

  ***REMOVED*** BYOV or create new (derived from use_byor_infrastructure)
  use_existing_network = local.use_existing_network

  ***REMOVED*** Existing network (BYOV)
  existing_vnet_name            = var.existing_vnet_name
  existing_resource_group_name  = var.existing_resource_group_name
  existing_public_subnet_name   = var.existing_public_subnet_name
  existing_private_subnet_name  = var.existing_private_subnet_name
  existing_nsg_name             = var.existing_nsg_name
  
  ***REMOVED*** NSG Association IDs (required for BYOV)
  existing_public_subnet_nsg_association_id  = var.existing_public_subnet_nsg_association_id
  existing_private_subnet_nsg_association_id = var.existing_private_subnet_nsg_association_id

  ***REMOVED*** New network configuration
  vnet_address_space            = var.vnet_address_space
  public_subnet_address_prefix  = var.public_subnet_address_prefix
  private_subnet_address_prefix = var.private_subnet_address_prefix

  ***REMOVED*** Non-PL pattern: NAT Gateway (derived from use_byor_infrastructure), Private Link disabled
  enable_nat_gateway  = local.enable_nat_gateway
  enable_private_link = false

  ***REMOVED*** Core configuration
  location            = var.location
  resource_group_name = local.resource_group_name
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
  workspace_name   = "${var.workspace_prefix}-workspace-${random_string.deployment_suffix.result}"
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
  cmk_key_vault_key_id        = local.cmk_enabled ? (local.create_key_vault ? module.key_vault[0].key_id : var.existing_key_id) : ""
  cmk_key_vault_id            = local.cmk_enabled ? (local.create_key_vault ? module.key_vault[0].key_vault_id : var.existing_key_vault_id) : ""
  databricks_account_id       = var.databricks_account_id

  ***REMOVED*** IP Access Lists (optional)
  enable_ip_access_lists = var.enable_ip_access_lists
  allowed_ip_ranges      = var.allowed_ip_ranges

  ***REMOVED*** Core configuration
  location            = var.location
  resource_group_name = local.resource_group_name
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
  enable_private_link_storage      = false  ***REMOVED*** Use Service Endpoints
  service_endpoints_enabled        = true
  enable_service_endpoint_policies = true

  ***REMOVED*** Access Connector
  create_access_connector               = var.create_access_connector
  existing_access_connector_id          = var.existing_access_connector_id
  existing_access_connector_principal_id = var.existing_access_connector_principal_id

  ***REMOVED*** Core configuration
  location            = var.location
  resource_group_name = local.resource_group_name
  tags                = local.all_tags

  depends_on = [module.workspace]
}

***REMOVED*** ==============================================
***REMOVED*** Service Endpoint Policy Module (Optional)
***REMOVED*** Restricts VNet egress to only allow-listed storage accounts
***REMOVED*** Applies to: Classic compute only (not serverless)
***REMOVED*** ==============================================

module "service_endpoint_policy" {
  count  = var.enable_service_endpoint_policy ? 1 : 0
  source = "../../modules/service-endpoint-policy"

  workspace_prefix   = var.workspace_prefix
  random_suffix      = random_string.deployment_suffix.result
  location           = var.location
  resource_group_name = local.resource_group_name

  ***REMOVED*** Storage accounts to allow-list
  dbfs_storage_resource_id          = module.workspace.dbfs_storage_account_id
  uc_metastore_storage_resource_id  = var.create_metastore ? module.unity_catalog.metastore_storage_account_id : ""
  uc_external_storage_resource_id   = module.unity_catalog.external_storage_account_id
  additional_storage_ids            = var.additional_allowed_storage_ids

  tags = local.all_tags

  depends_on = [module.workspace, module.unity_catalog]
}

***REMOVED*** ==============================================
***REMOVED*** Apply SEP to Subnets (Post-Deployment via Azure CLI)
***REMOVED*** ==============================================
***REMOVED*** Note: Cannot pass SEP ID to networking module during creation due to circular dependency:
***REMOVED*** Networking → Workspace → Unity Catalog → SEP → (back to Networking)
***REMOVED*** Solution: Apply SEP after all resources are created with built-in 30s sleep

resource "null_resource" "apply_sep_to_public_subnet" {
  count = var.enable_service_endpoint_policy && !local.use_existing_network ? 1 : 0

  triggers = {
    sep_id          = module.service_endpoint_policy[0].service_endpoint_policy_id
    subnet_id       = module.networking.subnet_ids["public"]
    storage_count   = module.service_endpoint_policy[0].allowed_storage_count
  }

  provisioner "local-exec" {
    command = <<-EOT
      echo "⏳ Waiting for SEP propagation..."
      sleep 30
      echo "Applying Service Endpoint Policy to public subnet..."
      az network vnet subnet update \
        --ids ${module.networking.subnet_ids["public"]} \
        --service-endpoint-policy ${module.service_endpoint_policy[0].service_endpoint_policy_id} \
        --output none
      echo "✅ SEP applied to public subnet"
    EOT
  }

  ***REMOVED*** Destroy-time provisioner: Remove SEP from subnet before policy deletion
  provisioner "local-exec" {
    when    = destroy
    command = <<-EOT
      echo "Removing Service Endpoint Policy from public subnet..."
      az network vnet subnet update \
        --ids ${self.triggers.subnet_id} \
        --remove serviceEndpointPolicies \
        --output none 2>/dev/null || echo "⚠️  Subnet or policy already removed"
      echo "✅ SEP removed from public subnet"
    EOT
  }

  depends_on = [module.service_endpoint_policy, module.networking, module.workspace, module.unity_catalog]
}

resource "null_resource" "apply_sep_to_private_subnet" {
  count = var.enable_service_endpoint_policy && !local.use_existing_network ? 1 : 0

  triggers = {
    sep_id          = module.service_endpoint_policy[0].service_endpoint_policy_id
    subnet_id       = module.networking.subnet_ids["private"]
    storage_count   = module.service_endpoint_policy[0].allowed_storage_count
  }

  provisioner "local-exec" {
    command = <<-EOT
      echo "⏳ Waiting for SEP propagation..."
      sleep 30
      echo "Applying Service Endpoint Policy to private subnet..."
      az network vnet subnet update \
        --ids ${module.networking.subnet_ids["private"]} \
        --service-endpoint-policy ${module.service_endpoint_policy[0].service_endpoint_policy_id} \
        --output none
      echo "✅ SEP applied to private subnet"
    EOT
  }

  ***REMOVED*** Destroy-time provisioner: Remove SEP from subnet before policy deletion
  provisioner "local-exec" {
    when    = destroy
    command = <<-EOT
      echo "Removing Service Endpoint Policy from private subnet..."
      az network vnet subnet update \
        --ids ${self.triggers.subnet_id} \
        --remove serviceEndpointPolicies \
        --output none 2>/dev/null || echo "⚠️  Subnet or policy already removed"
      echo "✅ SEP removed from private subnet"
    EOT
  }

  depends_on = [module.service_endpoint_policy, module.networking, module.workspace, module.unity_catalog]
}

***REMOVED*** ==============================================
***REMOVED*** Network Connectivity Configuration (NCC) Module
***REMOVED*** Mandatory for serverless compute (SQL Warehouses, Serverless Notebooks)
***REMOVED*** ==============================================

module "ncc" {
  source = "../../modules/ncc"

  providers = {
    databricks.account = databricks.account
  }

  ***REMOVED*** Workspace identification
  workspace_id_numeric = module.workspace.workspace_id_numeric
  workspace_prefix     = var.workspace_prefix
  location             = var.location

  ***REMOVED*** NCC configuration (empty - no PE rules)
  ***REMOVED*** PE rules for serverless storage access are created manually by customer
  ***REMOVED*** See docs/SERVERLESS-SETUP.md for setup instructions

  depends_on = [module.unity_catalog]
}
