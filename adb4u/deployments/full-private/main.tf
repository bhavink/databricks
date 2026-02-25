# ==============================================
# Full Private Azure Databricks Deployment
# ==============================================
#
# This deployment pattern creates a fully private (air-gapped) Azure Databricks
# workspace with the following characteristics:
#
# - Private Link for control plane (UI/API) access
# - Private Link for data plane (cluster-to-control-plane)
# - Secure Cluster Connectivity (NPIP - no public IPs)
# - NO NAT Gateway (air-gapped - no internet egress)
# - Private Endpoints for all storage (DBFS, UC Metastore, UC External)
# - Network Connectivity Configuration (NCC) for Databricks-managed private connectivity
# - Customer-Managed Keys (CMK) enabled by default
# - Unity Catalog with private storage access
#
# Prerequisites:
# - Azure subscription with appropriate permissions
# - Terraform >= 1.5
# - Environment variables set (see terraform.tfvars.example)
# - Customer must bring their own package repositories (PyPI, Maven, etc.)
#
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

  # DBFS storage account name (no special chars, lowercase)
  dbfs_storage_name = "${var.workspace_prefix}${random_string.deployment_suffix.result}dbfs"

  # Determine if any CMK feature is enabled
  cmk_enabled = var.enable_cmk_managed_services || var.enable_cmk_managed_disks || var.enable_cmk_dbfs_root

  # Derived flags based on use_byor_infrastructure
  use_existing_network = var.use_byor_infrastructure ? true : var.use_existing_network
  enable_nat_gateway   = var.use_byor_infrastructure ? false : var.enable_nat_gateway
  create_key_vault     = (var.use_byor_infrastructure && local.cmk_enabled) ? false : var.create_key_vault

  # Dynamically determine resource group name based on deployment mode
  resource_group_name = var.use_byor_infrastructure ? var.resource_group_name : azurerm_resource_group.this[0].name
}

# ==============================================
# Resource Group
# ==============================================

# Create Resource Group if not using BYOR infrastructure
resource "azurerm_resource_group" "this" {
  count    = var.use_byor_infrastructure ? 0 : 1
  name     = var.resource_group_name
  location = var.location
  tags     = local.all_tags
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
# Networking Module (VNet, Subnets, NSG, Private Link Subnet)
# ==============================================

module "networking" {
  source = "../../modules/networking"

  # BYOV or create new
  use_existing_network = local.use_existing_network

  # Existing network (BYOV)
  existing_vnet_name                         = var.existing_vnet_name
  existing_resource_group_name               = var.existing_resource_group_name
  existing_public_subnet_name                = var.existing_public_subnet_name
  existing_private_subnet_name               = var.existing_private_subnet_name
  existing_privatelink_subnet_name           = var.existing_privatelink_subnet_name
  existing_nsg_name                          = var.existing_nsg_name
  existing_public_subnet_nsg_association_id  = var.existing_public_subnet_nsg_association_id
  existing_private_subnet_nsg_association_id = var.existing_private_subnet_nsg_association_id

  # New network configuration
  vnet_address_space                = var.vnet_address_space
  public_subnet_address_prefix      = var.public_subnet_address_prefix
  private_subnet_address_prefix     = var.private_subnet_address_prefix
  privatelink_subnet_address_prefix = var.privatelink_subnet_address_prefix

  # Full Private pattern: Private Link enabled, NAT Gateway disabled (air-gapped)
  enable_private_link          = true
  enable_public_network_access = var.enable_public_network_access # Pass through to control NSG rule creation
  enable_nat_gateway           = local.enable_nat_gateway

  # Core configuration
  location            = var.location
  resource_group_name = local.resource_group_name
  workspace_prefix    = var.workspace_prefix
  tags                = local.all_tags

  depends_on = [azurerm_resource_group.this]
}

# ==============================================
# Workspace Module (Databricks Workspace with CMK)
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
  enable_private_link               = true                    # Full Private pattern
  dbfs_storage_name                 = local.dbfs_storage_name # Custom DBFS name

  # Customer-Managed Keys (enabled by default for Full Private)
  enable_cmk_managed_services = var.enable_cmk_managed_services
  enable_cmk_managed_disks    = var.enable_cmk_managed_disks
  enable_cmk_dbfs_root        = var.enable_cmk_dbfs_root
  cmk_key_vault_key_id        = local.cmk_enabled ? (local.create_key_vault ? module.key_vault[0].key_id : var.existing_key_id) : ""
  cmk_key_vault_id            = local.cmk_enabled ? (local.create_key_vault ? module.key_vault[0].key_vault_id : var.existing_key_vault_id) : ""
  databricks_account_id       = var.databricks_account_id

  # Network Access Control (public access enabled by default for deployment)
  enable_public_network_access = var.enable_public_network_access

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
# BYOR Validation (Ensure required inputs provided)
# ==============================================

resource "null_resource" "byor_network_validation" {
  count = var.use_byor_infrastructure ? 1 : 0

  lifecycle {
    precondition {
      condition = (
        var.existing_vnet_name != "" &&
        var.existing_resource_group_name != "" &&
        var.existing_public_subnet_name != "" &&
        var.existing_private_subnet_name != "" &&
        var.existing_privatelink_subnet_name != "" &&
        var.existing_nsg_name != "" &&
        var.existing_public_subnet_nsg_association_id != "" &&
        var.existing_private_subnet_nsg_association_id != ""
      )
      error_message = <<-EOT
        When use_byor_infrastructure=true, all existing network resources must be provided:
        - existing_vnet_name
        - existing_resource_group_name
        - existing_public_subnet_name
        - existing_private_subnet_name
        - existing_privatelink_subnet_name
        - existing_nsg_name
        - existing_public_subnet_nsg_association_id
        - existing_private_subnet_nsg_association_id
      EOT
    }
    precondition {
      condition = (
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

# ==============================================
# Private Endpoints Module (DNS + Private Endpoints)
# ==============================================

module "private_endpoints" {
  source = "../../modules/private-endpoints"

  # Workspace configuration
  workspace_id                        = module.workspace.workspace_id
  workspace_managed_resource_group_id = module.workspace.managed_resource_group_id
  workspace_prefix                    = var.workspace_prefix
  dbfs_storage_name                   = local.dbfs_storage_name

  # Network configuration
  vnet_id               = module.networking.vnet_id
  privatelink_subnet_id = module.networking.subnet_ids["privatelink"]

  # Unity Catalog storage (will be populated after UC module creates storage)
  create_uc_metastore_storage         = var.create_metastore
  uc_metastore_storage_account_id     = var.create_metastore ? module.unity_catalog.metastore_storage_account_id : ""
  uc_external_storage_account_id      = module.unity_catalog.external_storage_account_id
  enable_uc_storage_private_endpoints = true

  # Core configuration
  location            = var.location
  resource_group_name = local.resource_group_name
  tags                = local.all_tags

  depends_on = [module.workspace, module.unity_catalog]
}

# ==============================================
# Unity Catalog Module (Metastore, Storage, Access Connector)
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

  # Storage configuration (Full Private: Private Link for all storage)
  create_metastore_storage         = var.create_metastore
  create_external_location_storage = true
  enable_private_link_storage      = false # Private Endpoints created by private-endpoints module
  service_endpoints_enabled        = false # No Service Endpoints in air-gapped
  metastore_storage_name_prefix    = var.metastore_storage_name_prefix
  external_storage_name_prefix     = var.external_storage_name_prefix

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
# Network Connectivity Configuration (NCC) - OPTIONAL
# ==============================================
# NCC enables Databricks Serverless compute to access resources via Private Link.
# ⚠️  This module creates NCC config + binding ONLY.
# ⚠️  Storage Private Endpoint rules must be created manually (requires approval).
#
# Why Manual PE Rules?
# - PE connections from Databricks Control Plane require manual approval in Azure Portal
# - Terraform would timeout waiting for approval
# - Decouples deployment from manual workflows
#
# For classic clusters only, you can skip NCC (set enable_ncc = false)
# See: docs/04-SERVERLESS-SETUP.md for detailed serverless setup guide

module "ncc" {
  count  = var.enable_ncc ? 1 : 0
  source = "../../modules/ncc"

  providers = {
    databricks.account = databricks.account
  }

  # Workspace configuration
  workspace_id_numeric = module.workspace.workspace_id_numeric
  workspace_prefix     = var.workspace_prefix
  location             = var.location

  depends_on = [module.workspace]
}

# ==============================================
# Service Endpoint Policy (SEP) Module
# ==============================================

module "service_endpoint_policy" {
  count  = var.enable_service_endpoint_policy ? 1 : 0
  source = "../../modules/service-endpoint-policy"

  workspace_prefix    = var.workspace_prefix
  location            = var.location
  resource_group_name = local.resource_group_name

  dbfs_storage_resource_id         = module.workspace.dbfs_storage_account_id
  uc_metastore_storage_resource_id = var.create_metastore ? module.unity_catalog.metastore_storage_account_id : ""
  uc_external_storage_resource_id  = module.unity_catalog.external_storage_account_id
  additional_storage_ids           = var.additional_allowed_storage_ids
  random_suffix                    = random_string.deployment_suffix.result

  tags = local.all_tags

  depends_on = [module.workspace, module.unity_catalog]
}

# ==============================================
# Time Sleep (for SEP Propagation)
# ==============================================
# Azure requires time for SEP resources to fully propagate before subnet association
# This prevents "AnotherOperationInProgress" and "ResourceNotFound" errors

resource "time_sleep" "wait_for_sep" {
  count           = var.enable_service_endpoint_policy && !local.use_existing_network ? 1 : 0
  create_duration = "30s"

  depends_on = [module.service_endpoint_policy]
}

# ==============================================
# Apply SEP to Subnets (Post-Deployment via Azure CLI)
# ==============================================
# Note: Cannot pass SEP ID to networking module during creation due to circular dependency:
# Networking → Workspace → Unity Catalog → SEP → (back to Networking)
# Solution: Apply SEP after all resources are created

resource "null_resource" "apply_sep_to_public_subnet" {
  count = var.enable_service_endpoint_policy && !local.use_existing_network ? 1 : 0

  triggers = {
    subnet_id     = module.networking.subnet_ids["public"]
    sep_id        = module.service_endpoint_policy[0].service_endpoint_policy_id
    storage_count = length(module.service_endpoint_policy[0].allowed_storage_accounts)
  }

  provisioner "local-exec" {
    command = <<-EOT
      echo "⏳ Waiting for SEP propagation..."
      sleep 30
      echo "Applying Service Endpoint Policy to public subnet..."
      az network vnet subnet update \
        --resource-group ${local.resource_group_name} \
        --vnet-name ${module.networking.vnet_name} \
        --name ${module.networking.subnet_names["public"]} \
        --service-endpoint-policy "${module.service_endpoint_policy[0].service_endpoint_policy_id}" \
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

  depends_on = [
    module.networking,
    module.service_endpoint_policy,
    module.workspace,
    module.unity_catalog
  ]
}

resource "null_resource" "apply_sep_to_private_subnet" {
  count = var.enable_service_endpoint_policy && !local.use_existing_network ? 1 : 0

  triggers = {
    subnet_id     = module.networking.subnet_ids["private"]
    sep_id        = module.service_endpoint_policy[0].service_endpoint_policy_id
    storage_count = length(module.service_endpoint_policy[0].allowed_storage_accounts)
  }

  provisioner "local-exec" {
    command = <<-EOT
      echo "⏳ Waiting for SEP propagation..."
      sleep 30
      echo "Applying Service Endpoint Policy to private subnet..."
      az network vnet subnet update \
        --resource-group ${local.resource_group_name} \
        --vnet-name ${module.networking.vnet_name} \
        --name ${module.networking.subnet_names["private"]} \
        --service-endpoint-policy "${module.service_endpoint_policy[0].service_endpoint_policy_id}" \
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

  depends_on = [
    module.networking,
    module.service_endpoint_policy,
    module.workspace,
    module.unity_catalog
  ]
}

