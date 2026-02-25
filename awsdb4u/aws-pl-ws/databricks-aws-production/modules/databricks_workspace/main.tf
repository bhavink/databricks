# ============================================================================
# Databricks Workspace Module
# Creates MWS resources and Databricks workspace
# ============================================================================

terraform {
  required_providers {
    databricks = {
      source                = "databricks/databricks"
      version               = "~> 1.70" # Try latest to see if backend-only issue is fixed
      configuration_aliases = [databricks.account, databricks.workspace]
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.9"
    }
  }
}

# ============================================================================
# Local Variables
# ============================================================================

locals {
  # Create private_access_settings when Private Link is enabled
  # This resource contains both public_access_enabled (frontend) and private_access_level (backend)
  any_vpce_enabled = var.enable_private_link

  # Determine deployment type for documentation/logging
  vpce_deployment_type = var.enable_private_link ? "full_private_link" : "no_private_link"

  # PAS ID logic: Use existing if provided, otherwise use newly created (if VPCE enabled)
  # PAS is ACCOUNT-LEVEL and can be SHARED across multiple workspaces (typically in same transit VPC)
  should_create_pas = local.any_vpce_enabled && var.existing_private_access_settings_id == ""

  final_pas_id = (
    var.existing_private_access_settings_id != "" ? var.existing_private_access_settings_id :
    local.should_create_pas ? databricks_mws_private_access_settings.private_access[0].private_access_settings_id :
    null
  )
}

# ============================================================================
# Wait for IAM Propagation
# ============================================================================

resource "time_sleep" "wait_for_iam" {
  create_duration = "30s"

  depends_on = [var.cross_account_role_arn]
}

# ============================================================================
# Databricks Credential Configuration (Cross-Account Role)
# ============================================================================

resource "databricks_mws_credentials" "credentials" {
  provider         = databricks.account
  account_id       = var.databricks_account_id
  credentials_name = "${var.prefix}-credentials"
  role_arn         = var.cross_account_role_arn

  depends_on = [time_sleep.wait_for_iam]
}

# ============================================================================
# Databricks Storage Configuration (Root Storage Bucket)
# ============================================================================

resource "databricks_mws_storage_configurations" "storage" {
  provider                   = databricks.account
  account_id                 = var.databricks_account_id
  storage_configuration_name = "${var.prefix}-storage"
  bucket_name                = var.root_storage_bucket

  depends_on = [
    time_sleep.wait_for_iam
  ]
}

# ============================================================================
# Databricks Network Configuration (VPC, Subnets, Security Group)
# ============================================================================

resource "databricks_mws_networks" "network" {
  provider           = databricks.account
  account_id         = var.databricks_account_id
  network_name       = "${var.prefix}-network"
  vpc_id             = var.vpc_id
  subnet_ids         = var.private_subnet_ids
  security_group_ids = [var.workspace_security_group_id]

  # Conditionally include vpc_endpoints block when ANY VPC endpoint is enabled
  # IMPORTANT: Backend Private Link requires BOTH workspace + relay endpoints
  # - rest_api: Workspace endpoint (required for BOTH frontend and backend scenarios)
  #   - Frontend: UI/API access by users
  #   - Backend: Cluster REST API calls to control plane
  # - dataplane_relay: Relay endpoint (only required for backend scenarios)
  dynamic "vpc_endpoints" {
    for_each = local.any_vpce_enabled ? [1] : []

    content {
      rest_api        = [var.workspace_vpce_id] # Always populated when vpc_endpoints block exists
      dataplane_relay = var.enable_private_link ? [var.relay_vpce_id] : []
    }
  }

  depends_on = [
    var.workspace_vpce_id,
    var.relay_vpce_id
  ]
}

# ============================================================================
# Databricks Private Access Settings (Account-Level, Reusable Across Workspaces)
# Create only if:
#   1. ANY VPC endpoint is enabled (frontend or backend) AND
#   2. Existing PAS ID is NOT provided
# ============================================================================
# Architecture Note:
# - PAS is ACCOUNT-LEVEL and can be attached to MULTIPLE workspaces
# - Typically shared across workspaces in the same transit VPC (for frontend PL)
# - Network Configuration (below) is ONE-PER-WORKSPACE and cannot be shared
# ============================================================================

resource "databricks_mws_private_access_settings" "private_access" {
  count                        = local.should_create_pas ? 1 : 0
  provider                     = databricks.account
  account_id                   = var.databricks_account_id
  private_access_settings_name = "${var.prefix}-private-access"
  region                       = var.region

  # Frontend setting: Controls public internet access to workspace UI/API
  # Only relevant when Private Link is enabled
  # - true: Allow access via BOTH Private Link AND public internet
  # - false: ONLY allow access via Private Link (blocks public)
  public_access_enabled = var.public_access_enabled

  # Backend setting: Controls cluster communication method
  # Only relevant when Private Link is enabled
  # - "ACCOUNT": Uses public relay (default, recommended)
  # - "ENDPOINT": Uses backend VPC endpoint (advanced, must be tested)
  private_access_level = var.private_access_level

  depends_on = [
    var.workspace_vpce_id,
    var.relay_vpce_id
  ]
}

# ============================================================================
# Databricks Workspace
# ============================================================================

# Register Customer Managed Key for both Storage and Managed Services
resource "databricks_mws_customer_managed_keys" "workspace_cmk" {
  count = var.enable_workspace_cmk ? 1 : 0

  provider   = databricks.account
  account_id = var.databricks_account_id

  aws_key_info {
    key_arn   = var.workspace_storage_key_arn
    key_alias = var.workspace_storage_key_alias
  }

  use_cases = ["STORAGE", "MANAGED_SERVICES"]
}

resource "databricks_mws_workspaces" "workspace" {
  provider       = databricks.account
  account_id     = var.databricks_account_id
  workspace_name = var.workspace_name

  credentials_id           = databricks_mws_credentials.credentials.credentials_id
  storage_configuration_id = databricks_mws_storage_configurations.storage.storage_configuration_id
  network_id               = databricks_mws_networks.network.network_id

  # Set private_access_settings_id: Uses existing PAS or newly created PAS (if VPCE enabled)
  # PAS is ACCOUNT-LEVEL and can be SHARED across multiple workspaces
  private_access_settings_id = local.final_pas_id

  # Customer Managed Keys (Optional) - Same key for both storage and managed services
  managed_services_customer_managed_key_id = var.enable_workspace_cmk ? databricks_mws_customer_managed_keys.workspace_cmk[0].customer_managed_key_id : null
  storage_customer_managed_key_id          = var.enable_workspace_cmk ? databricks_mws_customer_managed_keys.workspace_cmk[0].customer_managed_key_id : null

  deployment_name = "${var.prefix}-workspace"
  aws_region      = var.region

  pricing_tier = "ENTERPRISE"

  depends_on = [
    databricks_mws_credentials.credentials,
    databricks_mws_storage_configurations.storage,
    databricks_mws_networks.network,
    databricks_mws_private_access_settings.private_access,
    var.workspace_vpce_id,
    var.relay_vpce_id
  ]
}

# ============================================================================
# NOTE: Workspace Admin Assignment
# The databricks_mws_permission_assignment API is not available for all workspace types.
# If you need to assign a workspace admin, do so manually via the Databricks UI after
# workspace creation, or use the account console.
# ============================================================================

# ============================================================================
# IP Access Lists Configuration (Optional)
# Enable IP-based access control for the workspace
# ============================================================================

resource "databricks_workspace_conf" "ip_access_lists" {
  count = var.enable_ip_access_lists ? 1 : 0

  provider = databricks.workspace

  custom_config = {
    "enableIpAccessLists" = "true"
  }

  depends_on = [databricks_mws_workspaces.workspace]
}

resource "databricks_ip_access_list" "allowed_list" {
  count = var.enable_ip_access_lists ? 1 : 0

  provider = databricks.workspace

  label        = "allowed-ips"
  list_type    = "ALLOW"
  ip_addresses = var.allowed_ip_addresses
  enabled      = true

  depends_on = [
    databricks_workspace_conf.ip_access_lists,
    databricks_mws_workspaces.workspace
  ]
}

