# ==============================================
# Diagnostic Settings (Workspace Audit Logs)
# ==============================================
# Exports Azure Databricks diagnostic logs to Log Analytics, Storage and/or
# Event Hub. Categories are discovered from Azure at plan time, so new log
# categories added by Azure Databricks are picked up without code changes.
# See: https://learn.microsoft.com/en-us/azure/databricks/admin/account-settings/audit-log-delivery

data "azurerm_monitor_diagnostic_categories" "workspace" {
  resource_id = var.workspace_id
}

resource "azurerm_monitor_diagnostic_setting" "workspace" {
  name                           = var.diagnostic_setting_name
  target_resource_id             = var.workspace_id
  log_analytics_workspace_id     = var.log_analytics_workspace_id != "" ? var.log_analytics_workspace_id : null
  storage_account_id             = var.storage_account_id != "" ? var.storage_account_id : null
  eventhub_authorization_rule_id = var.eventhub_authorization_rule_id != "" ? var.eventhub_authorization_rule_id : null
  eventhub_name                  = var.eventhub_name != "" ? var.eventhub_name : null

  dynamic "enabled_log" {
    for_each = data.azurerm_monitor_diagnostic_categories.workspace.log_category_types
    content {
      category = enabled_log.value
    }
  }

  lifecycle {
    precondition {
      condition     = var.log_analytics_workspace_id != "" || var.storage_account_id != "" || var.eventhub_authorization_rule_id != ""
      error_message = "Set at least one destination: log_analytics_workspace_id, storage_account_id or eventhub_authorization_rule_id."
    }
  }
}
