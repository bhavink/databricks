***REMOVED*** ==============================================
***REMOVED*** Network Connectivity Configuration (NCC)
***REMOVED*** ==============================================
***REMOVED***
***REMOVED*** NCC enables Databricks Serverless compute (SQL Warehouses, Serverless Notebooks)
***REMOVED*** to access resources via Private Link from Databricks Control Plane.
***REMOVED***
***REMOVED*** This module creates:
***REMOVED*** - NCC Configuration object
***REMOVED*** - NCC Binding to workspace
***REMOVED***
***REMOVED*** IMPORTANT: Private Endpoint Rules are NOT created by Terraform.
***REMOVED*** Customers must manually create PE rules via:
***REMOVED*** - Azure Portal (recommended for production)
***REMOVED*** - Databricks UI (workspace settings)
***REMOVED*** - Databricks REST API
***REMOVED***
***REMOVED*** Why Manual Creation?
***REMOVED*** - PE connections from Databricks Control Plane require manual approval
***REMOVED*** - Terraform would timeout waiting for approval
***REMOVED*** - Decouples deployment from manual approval workflow
***REMOVED***
***REMOVED*** See: docs/04-SERVERLESS-SETUP.md for detailed setup guide

***REMOVED*** Creates a Network Connectivity Configuration (NCC) in Databricks for managing
***REMOVED*** private connectivity to Azure resources from Databricks serverless compute.
resource "databricks_mws_network_connectivity_config" "this" {
  provider = databricks.account
  name     = "${var.workspace_prefix}-ncc"
  region   = var.location

  ***REMOVED*** Ensure binding is destroyed before NCC config
  lifecycle {
    create_before_destroy = false
  }
}

***REMOVED*** Binds the NCC configuration to the Databricks workspace
***REMOVED*** This enables serverless compute capability (SQL Warehouses, Serverless Notebooks)
resource "databricks_mws_ncc_binding" "this" {
  provider                       = databricks.account
  network_connectivity_config_id = databricks_mws_network_connectivity_config.this.network_connectivity_config_id
  workspace_id                   = var.workspace_id_numeric

  ***REMOVED*** Ensure binding is destroyed before NCC config
  lifecycle {
    create_before_destroy = false
  }
}
