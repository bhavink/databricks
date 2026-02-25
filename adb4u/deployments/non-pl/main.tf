# ==============================================
# Resource Group
# ==============================================

# Random suffix for unique resource naming
resource "random_string" "deployment_suffix" {
  length  = 4
  special = false
  upper   = false
  lower   = true
  numeric = true
}

locals {
  # Merge user-provided tags with required owner and keepuntil tags
  all_tags = merge(
    var.tags,
    {
      Owner     = var.tag_owner
      KeepUntil = var.tag_keepuntil
    }
  )

  # Add suffix to metastore name for uniqueness
  metastore_name_with_suffix = var.metastore_name != "" ? "${var.metastore_name}-${random_string.deployment_suffix.result}" : ""

  # Determine if any CMK feature is enabled
  cmk_enabled = var.enable_cmk_managed_services || var.enable_cmk_managed_disks || var.enable_cmk_dbfs_root

  # ==============================================
  # BYOR Derived Flags (Master Control Logic)
  # ==============================================
  # When use_byor_infrastructure=true, automatically derive correct flags
  # to prevent user configuration errors.

  # Network: Use BYOR network if use_byor_infrastructure is true
  use_existing_network = var.use_byor_infrastructure ? true : var.use_existing_network

  # NAT Gateway: BYOR already created it, so disable workspace creation
  enable_nat_gateway = var.use_byor_infrastructure ? false : var.enable_nat_gateway

  # CMK Key Vault: BYOR already created it (if CMK enabled), so use existing
  create_key_vault = (var.use_byor_infrastructure && local.cmk_enabled) ? false : var.create_key_vault
}

# ==============================================
# Resource Group
# ==============================================

# Create new Resource Group only when not using BYOR
resource "azurerm_resource_group" "this" {
  count    = var.use_byor_infrastructure ? 0 : 1
  name     = var.resource_group_name
  location = var.location
  tags     = local.all_tags

  # Validation: When using BYOR, ensure network resources are provided
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

# Local to use either existing or newly created RG name
locals {
  # When using BYOR, RG already exists - just use the variable
  # When not using BYOR, use the newly created RG name
  resource_group_name = var.use_byor_infrastructure ? var.resource_group_name : azurerm_resource_group.this[0].name
}

# ==============================================
# Key Vault Module (Optional - for CMK)
# ==============================================

# Only invoke key_vault module if creating a new Key Vault
module "key_vault" {
  count  = local.cmk_enabled && local.create_key_vault ? 1 : 0
  source = "../../modules/key-vault"

  # Create or use existing Key Vault
  create_key_vault      = local.create_key_vault
  existing_key_vault_id = var.existing_key_vault_id
  existing_key_id       = var.existing_key_id

  # Resource configuration
  workspace_prefix    = var.workspace_prefix
  resource_group_name = local.resource_group_name
  location            = var.location

  # Key configuration (auto-rotation enabled)
  key_name             = "databricks-cmk"
  enable_auto_rotation = true
  rotation_policy_days = 90

  # Security configuration
  enable_purge_protection    = true
  soft_delete_retention_days = 90

  tags = local.all_tags

  depends_on = [azurerm_resource_group.this]
}

# ==============================================
# Networking Module
# ==============================================

module "networking" {
  source = "../../modules/networking"

  # BYOV or create new (derived from use_byor_infrastructure)
  use_existing_network = local.use_existing_network

  # Existing network (BYOV)
  existing_vnet_name           = var.existing_vnet_name
  existing_resource_group_name = var.existing_resource_group_name
  existing_public_subnet_name  = var.existing_public_subnet_name
  existing_private_subnet_name = var.existing_private_subnet_name
  existing_nsg_name            = var.existing_nsg_name

  # NSG Association IDs (required for BYOV)
  existing_public_subnet_nsg_association_id  = var.existing_public_subnet_nsg_association_id
  existing_private_subnet_nsg_association_id = var.existing_private_subnet_nsg_association_id

  # New network configuration
  vnet_address_space            = var.vnet_address_space
  public_subnet_address_prefix  = var.public_subnet_address_prefix
  private_subnet_address_prefix = var.private_subnet_address_prefix

  # Non-PL pattern: NAT Gateway (derived from use_byor_infrastructure), Private Link disabled
  enable_nat_gateway  = local.enable_nat_gateway
  enable_private_link = false

  # Core configuration
  location            = var.location
  resource_group_name = local.resource_group_name
  workspace_prefix    = var.workspace_prefix
  tags                = local.all_tags

  depends_on = [azurerm_resource_group.this]
}

# ==============================================
# Workspace Module
# ==============================================

module "workspace" {
  source = "../../modules/workspace"

  # Workspace configuration
  workspace_name   = "${var.workspace_prefix}-workspace-${random_string.deployment_suffix.result}"
  workspace_prefix = var.workspace_prefix

  # Networking
  vnet_id                           = module.networking.vnet_id
  public_subnet_name                = module.networking.subnet_names["public"]
  private_subnet_name               = module.networking.subnet_names["private"]
  public_subnet_nsg_association_id  = module.networking.public_subnet_nsg_association_id
  private_subnet_nsg_association_id = module.networking.private_subnet_nsg_association_id
  enable_private_link               = false # Non-PL pattern

  # Customer-Managed Keys (optional)
  enable_cmk_managed_services = var.enable_cmk_managed_services
  enable_cmk_managed_disks    = var.enable_cmk_managed_disks
  enable_cmk_dbfs_root        = var.enable_cmk_dbfs_root
  cmk_key_vault_key_id        = local.cmk_enabled ? (local.create_key_vault ? module.key_vault[0].key_id : var.existing_key_id) : ""
  cmk_key_vault_id            = local.cmk_enabled ? (local.create_key_vault ? module.key_vault[0].key_vault_id : var.existing_key_vault_id) : ""
  databricks_account_id       = var.databricks_account_id

  # IP Access Lists (optional)
  enable_ip_access_lists = var.enable_ip_access_lists
  allowed_ip_ranges      = var.allowed_ip_ranges

  # Core configuration
  location            = var.location
  resource_group_name = local.resource_group_name
  tags                = local.all_tags

  depends_on = [module.networking]
}

# ==============================================
# Unity Catalog Module
# ==============================================

module "unity_catalog" {
  source = "../../modules/unity-catalog"

  providers = {
    databricks.account   = databricks.account
    databricks.workspace = databricks.workspace
  }

  # Metastore configuration
  create_metastore      = var.create_metastore
  existing_metastore_id = var.existing_metastore_id
  metastore_name        = local.metastore_name_with_suffix
  databricks_account_id = var.databricks_account_id

  # Workspace
  workspace_id     = module.workspace.workspace_id_numeric # Numeric ID for Unity Catalog
  workspace_prefix = var.workspace_prefix

  # Storage configuration (Non-PL: Service Endpoints)
  create_metastore_storage         = var.create_metastore
  create_external_location_storage = true
  enable_private_link_storage      = false # Use Service Endpoints
  service_endpoints_enabled        = true
  enable_service_endpoint_policies = true

  # Access Connector
  create_access_connector                = var.create_access_connector
  existing_access_connector_id           = var.existing_access_connector_id
  existing_access_connector_principal_id = var.existing_access_connector_principal_id

  # Core configuration
  location            = var.location
  resource_group_name = local.resource_group_name
  tags                = local.all_tags

  depends_on = [module.workspace]
}

# ==============================================
# Service Endpoint Policy Module (Optional)
# Restricts VNet egress to only allow-listed storage accounts
# Applies to: Classic compute only (not serverless)
# ==============================================

module "service_endpoint_policy" {
  count  = var.enable_service_endpoint_policy ? 1 : 0
  source = "../../modules/service-endpoint-policy"

  workspace_prefix    = var.workspace_prefix
  random_suffix       = random_string.deployment_suffix.result
  location            = var.location
  resource_group_name = local.resource_group_name

  # Storage accounts to allow-list
  dbfs_storage_resource_id         = module.workspace.dbfs_storage_account_id
  uc_metastore_storage_resource_id = var.create_metastore ? module.unity_catalog.metastore_storage_account_id : ""
  uc_external_storage_resource_id  = module.unity_catalog.external_storage_account_id
  additional_storage_ids           = var.additional_allowed_storage_ids

  tags = local.all_tags

  depends_on = [module.workspace, module.unity_catalog]
}

# ==============================================
# Apply SEP to Subnets (Post-Deployment via Azure CLI)
# ==============================================
# Note: Cannot pass SEP ID to networking module during creation due to circular dependency:
# Networking → Workspace → Unity Catalog → SEP → (back to Networking)
# Solution: Apply SEP after all resources are created with built-in 30s sleep

resource "null_resource" "apply_sep_to_public_subnet" {
  count = var.enable_service_endpoint_policy && !local.use_existing_network ? 1 : 0

  triggers = {
    sep_id        = module.service_endpoint_policy[0].service_endpoint_policy_id
    subnet_id     = module.networking.subnet_ids["public"]
    storage_count = module.service_endpoint_policy[0].allowed_storage_count
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

  # Destroy-time provisioner: Remove SEP from subnet before policy deletion
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
    sep_id        = module.service_endpoint_policy[0].service_endpoint_policy_id
    subnet_id     = module.networking.subnet_ids["private"]
    storage_count = module.service_endpoint_policy[0].allowed_storage_count
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

  # Destroy-time provisioner: Remove SEP from subnet before policy deletion
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

# ==============================================
# Network Connectivity Configuration (NCC) Module
# Mandatory for serverless compute (SQL Warehouses, Serverless Notebooks)
# ==============================================

module "ncc" {
  source = "../../modules/ncc"

  providers = {
    databricks.account = databricks.account
  }

  # Workspace identification
  workspace_id_numeric = module.workspace.workspace_id_numeric
  workspace_prefix     = var.workspace_prefix
  location             = var.location

  # NCC configuration (empty - no PE rules)
  # PE rules for serverless storage access are created manually by customer
  # See docs/SERVERLESS-SETUP.md for setup instructions

  depends_on = [module.unity_catalog]
}
