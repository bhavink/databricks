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
