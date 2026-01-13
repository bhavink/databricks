***REMOVED*** ==============================================
***REMOVED*** Service Endpoint Policy Outputs
***REMOVED*** ==============================================

output "service_endpoint_policy_id" {
  description = "ID of the Service Endpoint Policy for subnet association"
  value       = azurerm_subnet_service_endpoint_storage_policy.this.id
}

output "service_endpoint_policy_name" {
  description = "Name of the Service Endpoint Policy"
  value       = azurerm_subnet_service_endpoint_storage_policy.this.name
}

output "allowed_storage_accounts" {
  description = "List of allowed storage account resource IDs in the policy"
  value = concat(
    [var.dbfs_storage_resource_id],
    var.uc_metastore_storage_resource_id != "" ? [var.uc_metastore_storage_resource_id] : [],
    var.uc_external_storage_resource_id != "" ? [var.uc_external_storage_resource_id] : [],
    var.additional_storage_ids
  )
}

output "allowed_storage_count" {
  description = "Total number of allowed storage accounts"
  value = length(concat(
    [var.dbfs_storage_resource_id],
    var.uc_metastore_storage_resource_id != "" ? [var.uc_metastore_storage_resource_id] : [],
    var.uc_external_storage_resource_id != "" ? [var.uc_external_storage_resource_id] : [],
    var.additional_storage_ids
  ))
}
