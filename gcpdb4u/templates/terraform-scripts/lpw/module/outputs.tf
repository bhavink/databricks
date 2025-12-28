***REMOVED*** ============================================================================
***REMOVED*** PHASE 1 OUTPUTS - Workspace and Network
***REMOVED*** ============================================================================

output "workspace_id" {
  description = "Databricks workspace ID"
  value       = databricks_mws_workspaces.dbx_workspace.workspace_id
}

output "workspace_url" {
  description = "Databricks workspace URL"
  value       = databricks_mws_workspaces.dbx_workspace.workspace_url
}

output "workspace_name" {
  description = "Databricks workspace name"
  value       = databricks_mws_workspaces.dbx_workspace.workspace_name
}

output "workspace_status" {
  description = "Current workspace status"
  value       = databricks_mws_workspaces.dbx_workspace.workspace_status
}

output "workspace_gcp_service_account" {
  description = "GCP service account for the workspace"
  value       = databricks_mws_workspaces.dbx_workspace.gcp_workspace_sa
}

***REMOVED*** MODIFICATION: Added workspace GSA email output
***REMOVED*** Reason: Make workspace GSA email easily accessible for reference and verification
***REMOVED*** NOTE: Manual action required - add this GSA to your operator group manually
output "workspace_gsa_email" {
  description = "Workspace Google Service Account email (db-* format) - MANUAL ACTION: Add to operator group"
  value       = local.workspace_gsa_email
}

***REMOVED*** COMMENTED OUT: workspace_operator_group_email output (group membership feature disabled)
***REMOVED*** output "workspace_operator_group_email" {
***REMOVED***   description = "Google Workspace Group email that workspace GSA was added to"
***REMOVED***   value       = var.workspace_operator_group_email
***REMOVED*** }

output "network_id" {
  description = "Network configuration ID"
  value       = databricks_mws_networks.dbx_network.network_id
}

output "network_name" {
  description = "Network configuration name"
  value       = databricks_mws_networks.dbx_network.network_name
}

output "mws_network" {
  description = "Full network resource"
  value       = databricks_mws_networks.dbx_network
  sensitive   = true
}

output "workspace_full" {
  description = "Full workspace resource"
  value       = databricks_mws_workspaces.dbx_workspace
  sensitive   = true
}

***REMOVED*** ============================================================================
***REMOVED*** PHASE 3 OUTPUTS - Workspace Resources
***REMOVED*** ============================================================================

output "databricks_host" {
  description = "Databricks workspace host URL"
  value       = "https://${databricks_mws_workspaces.dbx_workspace.workspace_url}"
}

output "databricks_unity_catalog" {
  description = "Unity catalog details"
  value = var.provision_workspace_resources ? [
    for catalog in databricks_catalog.workspace_catalog : {
      name         = catalog.name
      owner        = catalog.owner
      storage_root = catalog.storage_root
      catalog_id   = catalog.id
    }
  ] : []
}

output "databricks_external_location" {
  description = "External location details"
  value = var.provision_workspace_resources ? [
    for location in databricks_external_location.external_location : {
      name        = location.name
      url         = location.url
      credential  = location.credential_name
      location_id = location.id
    }
  ] : []
}

output "databricks_storage_credentials" {
  description = "Storage credentials details"
  value = var.provision_workspace_resources ? [
    for cred in databricks_storage_credential.this : {
      name                           = cred.name
      databricks_gcp_service_account = cred.databricks_gcp_service_account
      credential_id                  = cred.id
    }
  ] : []
}

output "databricks_sql_warehouse" {
  description = "SQL warehouse details"
  value = var.provision_workspace_resources ? [
    for warehouse in databricks_sql_endpoint.this : {
      name           = warehouse.name
      cluster_size   = warehouse.cluster_size
      warehouse_type = warehouse.warehouse_type
      warehouse_id   = warehouse.id
      jdbc_url       = warehouse.jdbc_url
      odbc_params    = warehouse.odbc_params
    }
  ] : []
}

output "databricks_instance_pools" {
  description = "Instance pool details"
  value = var.provision_workspace_resources ? [
    for pool in databricks_instance_pool.compute_pools : {
      name         = pool.instance_pool_name
      node_type    = pool.node_type_id
      max_capacity = pool.max_capacity
      pool_id      = pool.id
    }
  ] : []
}

output "databricks_cluster_policies" {
  description = "Cluster policy details"
  value = var.provision_workspace_resources ? merge(
    {
      for policy in databricks_cluster_policy.this : policy.name => {
        policy_id = policy.id
        name      = policy.name
      }
    },
    var.provision_workspace_resources && length(databricks_cluster_policy.personal_vm) > 0 ? {
      "Personal VM" = {
        policy_id = databricks_cluster_policy.personal_vm[0].id
        name      = databricks_cluster_policy.personal_vm[0].name
      }
    } : {},
    var.provision_workspace_resources && length(databricks_cluster_policy.shared_compute) > 0 ? {
      "Shared Compute" = {
        policy_id = databricks_cluster_policy.shared_compute[0].id
        name      = databricks_cluster_policy.shared_compute[0].name
      }
    } : {}
  ) : {}
}

output "gcs_buckets" {
  description = "GCS bucket details"
  value = var.provision_workspace_resources ? merge(
    {
      for bucket in google_storage_bucket.internal_bucket : bucket.name => {
        bucket_name = bucket.name
        location    = bucket.location
        url         = bucket.url
      }
    },
    {
      for bucket in google_storage_bucket.external_bucket : bucket.name => {
        bucket_name = bucket.name
        location    = bucket.location
        url         = bucket.url
      }
    }
  ) : {}
}

***REMOVED*** ============================================================================
***REMOVED*** RESOURCE COUNTS (for verification)
***REMOVED*** ============================================================================

output "resource_counts" {
  description = "Count of resources created by phase"
  value = {
    phase_1_resources = 2                                                  ***REMOVED*** Always: network + workspace
    phase_2_resources = var.expected_workspace_status == "RUNNING" ? 1 : 0 ***REMOVED*** null_resource polling
    phase_3_resources = var.provision_workspace_resources ? {
      instance_pools      = length(databricks_instance_pool.compute_pools)
      cluster_policies    = length(databricks_cluster_policy.this) + (length(databricks_cluster_policy.personal_vm) > 0 ? 1 : 0) + (length(databricks_cluster_policy.shared_compute) > 0 ? 1 : 0)
      sql_warehouses      = length(databricks_sql_endpoint.this)
      unity_catalogs      = length(databricks_catalog.workspace_catalog)
      external_locations  = length(databricks_external_location.external_location)
      storage_credentials = length(databricks_storage_credential.this)
      gcs_buckets         = length(google_storage_bucket.internal_bucket) + length(google_storage_bucket.external_bucket)
    } : {}
  }
}

