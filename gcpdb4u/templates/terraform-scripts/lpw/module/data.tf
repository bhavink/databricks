
data "databricks_group" "group_role_admin" {
  provider     = databricks.accounts
  for_each     = (var.provision_workspace_resources && local.create_group_admin) ? toset([for admin in local.permissions_group_role_admin_list : trimspace(admin)]) : []
  display_name = each.value
}

data "databricks_group" "group_role_user" {
  provider     = databricks.accounts
  for_each     = (var.provision_workspace_resources && local.create_group_user) ? toset([for user in local.permissions_group_role_user_list : trimspace(user)]) : []
  display_name = each.value
}


data "databricks_user" "user_role_admin" {
  provider  = databricks.accounts
  for_each  = (var.provision_workspace_resources && local.create_user_admin) ? toset([for admin in local.permissions_user_role_admin_list : trimspace(admin)]) : []
  user_name = each.value
}

data "databricks_user" "user_role_user" {
  provider  = databricks.accounts
  for_each  = (var.provision_workspace_resources && local.create_user_user) ? toset([for user in local.permissions_user_role_user_list : trimspace(user)]) : []
  user_name = each.value
}


data "databricks_service_principal" "spn_role_admin" {
  provider     = databricks.accounts
  for_each     = (var.provision_workspace_resources && local.create_spn_admin) ? toset([for admin in local.permissions_spn_role_admin_list : trimspace(admin)]) : []
  display_name = each.value
}

data "databricks_service_principal" "spn_role_user" {
  provider     = databricks.accounts
  for_each     = (var.provision_workspace_resources && local.create_spn_user) ? toset([for user in local.permissions_spn_role_user_list : trimspace(user)]) : []
  display_name = each.value
}



***REMOVED***gcs
data "google_storage_bucket" "external_bucket" {
  for_each   = var.external_project && var.provision_workspace_resources ? local.unity_catalog_config_map : {}
  provider   = google.external
  name       = each.value.external_bucket
  depends_on = [google_storage_bucket.external_bucket]
}

data "google_storage_bucket" "internal_bucket" {
  for_each   = !var.external_project && var.provision_workspace_resources ? local.unity_catalog_config_map : {}
  provider   = google.internal
  name       = each.value.external_bucket
  depends_on = [google_storage_bucket.internal_bucket]
}