resource "google_storage_bucket" "internal_bucket" {
  location = var.environment == "prod" ? "us" : (var.environment == "dev" || var.environment == "stage" ? var.google_region : "us")

  provider                 = google.internal
  for_each                 = var.external_project ? {} : (var.provision_workspace_resources ? local.unity_catalog_config_map : {})
  name                     = each.value.external_bucket
  public_access_prevention = "enforced"
  labels = {
    "applicationname" = var.workspace_name
    "apmid"           = lower(var.apmid)
    "trproductid"     = var.trproductid
    "costcenter"      = lower(var.costcenter)
    "ssp"             = lower(var.ssp)
    "environment"     = lower(var.environment)
  }
  ***REMOVED*** MODIFICATION - added null_resource.wait_for_workspace_running dependency to make sure that workspace is in running state
  depends_on = [databricks_storage_credential.this, null_resource.wait_for_workspace_running]
}


resource "google_storage_bucket" "external_bucket" {
  location = var.environment == "prod" ? "us" : (var.environment == "dev" || var.environment == "stage" ? var.google_region : "us")

  provider                 = google.external
  for_each                 = var.external_project ? (var.provision_workspace_resources ? local.unity_catalog_config_map : {}) : {}
  name                     = each.value.external_bucket
  public_access_prevention = "enforced"
  labels = {
    "applicationname" = var.workspace_name
    "apmid"           = lower(var.apmid)
    "trproductid"     = var.trproductid
    "costcenter"      = lower(var.costcenter)
    "ssp"             = lower(var.ssp)
    "environment"     = lower(var.environment)
  }
  ***REMOVED*** MODIFICATION - added null_resource.wait_for_workspace_running dependency to make sure that workspace is in running state
  depends_on = [databricks_storage_credential.this, null_resource.wait_for_workspace_running]
}