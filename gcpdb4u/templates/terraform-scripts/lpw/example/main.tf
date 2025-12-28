module "local_databricks" {
  ***REMOVED*** MODIFICATION: Phase-driven deployment using single variable
  ***REMOVED*** Reason: Simplified deployment - use terraform apply -var="phase=PROVISIONING" or -var="phase=RUNNING"
  expected_workspace_status = local.current_phase.expected_workspace_status
  ***REMOVED*** MODIFICATION: Safe provisioning flag ensures resources only created after workspace is RUNNING
  provision_workspace_resources = local.safe_provision_resources

  source = "../module"

  ***REMOVED*** Databricks Account Configuration - passed from root module variables
  databricks_account_id             = var.databricks_account_id
  databricks_google_service_account = var.databricks_google_service_account

  ***REMOVED*** Regional Configuration
  private_access_settings_id      = var.private_access_settings_id
  dataplane_relay_vpc_endpoint_id = var.dataplane_relay_vpc_endpoint_id
  rest_api_vpc_endpoint_id        = var.rest_api_vpc_endpoint_id
  databricks_metastore_id         = var.databricks_metastore_id

  ***REMOVED*** Workspace Configuration
  workspace_name = var.workspace_name
  metastore_id   = var.metastore_id

  ***REMOVED*** Network Configuration
  network_project_id = var.network_project_id
  vpc_id             = var.vpc_id
  subnet_id          = var.subnet_id

  ***REMOVED*** Metadata and Tags
  notificationdistlist = var.notificationdistlist
  teamname             = var.teamname
  org                  = var.org
  owner                = var.owner
  costcenter           = var.costcenter
  environment          = var.environment
  apmid                = var.apmid
  ssp                  = var.ssp
  trproductid          = var.trproductid
  applicationtier      = var.applicationtier

  ***REMOVED*** GCP Project Configuration
  gcpprojectid        = var.gcpprojectid
  google_project_name = var.google_project_name
  google_region       = var.google_region

  ***REMOVED*** Compute Configuration
  node_type     = var.node_type
  compute_types = var.compute_types

  ***REMOVED*** Permissions
  cluster_policy_permissions   = var.cluster_policy_permissions
  pool_usage_permissions       = var.pool_usage_permissions
  permissions_group_role_user  = var.permissions_group_role_user
  permissions_group_role_admin = var.permissions_group_role_admin
  permissions_user_role_user   = var.permissions_user_role_user
  permissions_spn_role_user    = var.permissions_spn_role_user
  permissions_spn_role_admin   = var.permissions_spn_role_admin

  ***REMOVED*** External Project Configuration
  external_project  = var.external_project
  bucket_project_id = var.bucket_project_id

  ***REMOVED*** Unity Catalog Configuration
  unity_catalog_config            = var.unity_catalog_config
  unity_catalog_permissions       = var.unity_catalog_permissions
  external_location_permissions   = var.external_location_permissions
  storage_credentials_permissions = var.storage_credentials_permissions

  ***REMOVED*** SQL Warehouse Configuration
  sqlwarehouse_cluster_config = var.sqlwarehouse_cluster_config
}
