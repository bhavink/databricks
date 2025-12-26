***REMOVED*** ============================================================================
***REMOVED*** Databricks Workspace Module
***REMOVED*** Creates MWS resources and Databricks workspace
***REMOVED*** ============================================================================

terraform {
  required_providers {
    databricks = {
      source                = "databricks/databricks"
      version               = "~> 1.50"
      configuration_aliases = [databricks.account, databricks.workspace]
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.9"
    }
  }
}

***REMOVED*** ============================================================================
***REMOVED*** Wait for IAM Propagation
***REMOVED*** ============================================================================

resource "time_sleep" "wait_for_iam" {
  create_duration = "30s"

  depends_on = [var.cross_account_role_arn]
}

***REMOVED*** ============================================================================
***REMOVED*** Databricks Credential Configuration (Cross-Account Role)
***REMOVED*** ============================================================================

resource "databricks_mws_credentials" "credentials" {
  provider         = databricks.account
  account_id       = var.databricks_account_id
  credentials_name = "${var.prefix}-credentials"
  role_arn         = var.cross_account_role_arn

  depends_on = [time_sleep.wait_for_iam]
}

***REMOVED*** ============================================================================
***REMOVED*** Databricks Storage Configuration (Root Storage Bucket)
***REMOVED*** ============================================================================

resource "databricks_mws_storage_configurations" "storage" {
  provider                   = databricks.account
  account_id                 = var.databricks_account_id
  storage_configuration_name = "${var.prefix}-storage"
  bucket_name                = var.root_storage_bucket

  depends_on = [
    time_sleep.wait_for_iam
  ]
}

***REMOVED*** ============================================================================
***REMOVED*** Databricks Network Configuration (VPC, Subnets, Security Group)
***REMOVED*** ============================================================================

resource "databricks_mws_networks" "network" {
  provider           = databricks.account
  account_id         = var.databricks_account_id
  network_name       = "${var.prefix}-network"
  vpc_id             = var.vpc_id
  subnet_ids         = var.private_subnet_ids
  security_group_ids = [var.workspace_security_group_id]

  ***REMOVED*** Reference the Databricks-registered VPC endpoints for Private Link
  vpc_endpoints {
    dataplane_relay = [var.relay_vpce_id]
    rest_api        = [var.workspace_vpce_id]
  }

  depends_on = [
    var.workspace_vpce_id,
    var.relay_vpce_id
  ]
}

***REMOVED*** ============================================================================
***REMOVED*** Databricks Private Access Settings (Backend Private Link)
***REMOVED*** ============================================================================

resource "databricks_mws_private_access_settings" "private_access" {
  provider                     = databricks.account
  account_id                   = var.databricks_account_id
  private_access_settings_name = "${var.prefix}-private-access"
  region                       = var.region
  public_access_enabled        = var.public_access_enabled

  private_access_level = var.private_access_level

  depends_on = [
    var.workspace_vpce_id,
    var.relay_vpce_id
  ]
}

***REMOVED*** ============================================================================
***REMOVED*** Databricks Workspace
***REMOVED*** ============================================================================

***REMOVED*** Register Customer Managed Key for both Storage and Managed Services
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

  private_access_settings_id = databricks_mws_private_access_settings.private_access.private_access_settings_id

  ***REMOVED*** Customer Managed Keys (Optional) - Same key for both storage and managed services
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

***REMOVED*** ============================================================================
***REMOVED*** NOTE: Workspace Admin Assignment
***REMOVED*** The databricks_mws_permission_assignment API is not available for all workspace types.
***REMOVED*** If you need to assign a workspace admin, do so manually via the Databricks UI after
***REMOVED*** workspace creation, or use the account console.
***REMOVED*** ============================================================================

***REMOVED*** ============================================================================
***REMOVED*** IP Access Lists Configuration (Optional)
***REMOVED*** Enable IP-based access control for the workspace
***REMOVED*** ============================================================================

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

