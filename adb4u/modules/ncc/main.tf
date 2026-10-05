# ==============================================
# Network Connectivity Configuration (NCC)
# ==============================================
#
# NCC enables Databricks Serverless compute (SQL Warehouses, Serverless Notebooks)
# to access resources via Private Link from Databricks Control Plane.
#
# This module creates:
# - NCC Configuration object
# - NCC Binding to workspace
#
# IMPORTANT: Private Endpoint Rules are NOT created by Terraform.
# Customers must manually create PE rules via:
# - Azure Portal (recommended for production)
# - Databricks UI (workspace settings)
# - Databricks REST API
#
# Why Manual Creation?
# - PE connections from Databricks Control Plane require manual approval
# - Terraform would timeout waiting for approval
# - Decouples deployment from manual approval workflow
#
# See: docs/04-SERVERLESS-SETUP.md for detailed setup guide

# Creates a Network Connectivity Configuration (NCC) in Databricks for managing
# private connectivity to Azure resources from Databricks serverless compute.
resource "databricks_mws_network_connectivity_config" "this" {
  provider = databricks.account
  name     = "${var.workspace_prefix}-ncc"
  region   = var.location

  # Ensure binding is destroyed before NCC config
  lifecycle {
    create_before_destroy = false
  }
}

# Binds the NCC configuration to the Databricks workspace
# This enables serverless compute capability (SQL Warehouses, Serverless Notebooks)
resource "databricks_mws_ncc_binding" "this" {
  provider                       = databricks.account
  network_connectivity_config_id = databricks_mws_network_connectivity_config.this.network_connectivity_config_id
  workspace_id                   = var.workspace_id_numeric

  # Ensure binding is destroyed before NCC config
  lifecycle {
    create_before_destroy = false
  }
}

# ==============================================
# Serverless Network Policy (Optional)
# ==============================================
# Restricts serverless egress. Each workspace has exactly one network policy
# (default: "default-policy", full access); this assigns a restricted one.

resource "databricks_account_network_policy" "this" {
  count    = var.enable_network_policy ? 1 : 0
  provider = databricks.account

  network_policy_id = "${var.workspace_prefix}-restricted"

  egress = {
    network_access = {
      restriction_mode = "RESTRICTED_ACCESS"
      allowed_internet_destinations = [
        for d in var.allowed_internet_destinations : {
          destination               = d
          internet_destination_type = "DNS_NAME"
        }
      ]
      allowed_storage_destinations = [
        for a in var.allowed_storage_accounts : {
          azure_storage_account    = a
          azure_storage_service    = "dfs"
          storage_destination_type = "AZURE_STORAGE"
        }
      ]
      policy_enforcement = {
        enforcement_mode = var.network_policy_enforcement_mode
      }
    }
  }
}

resource "databricks_workspace_network_option" "this" {
  count    = var.enable_network_policy ? 1 : 0
  provider = databricks.account

  workspace_id      = var.workspace_id_numeric
  network_policy_id = databricks_account_network_policy.this[0].network_policy_id
}
