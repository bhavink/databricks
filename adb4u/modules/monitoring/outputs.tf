output "diagnostic_setting_id" {
  description = "Diagnostic setting resource ID"
  value       = azurerm_monitor_diagnostic_setting.workspace.id
}

output "log_categories" {
  description = "Diagnostic log categories enabled"
  value       = data.azurerm_monitor_diagnostic_categories.workspace.log_category_types
}
