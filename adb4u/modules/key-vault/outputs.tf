# ==============================================
# Key Vault Outputs
# ==============================================

output "key_vault_id" {
  description = "Key Vault resource ID"
  value       = local.key_vault_id
}

output "key_vault_name" {
  description = "Key Vault name"
  value       = var.create_key_vault ? azurerm_key_vault.this[0].name : ""
}

output "key_vault_uri" {
  description = "Key Vault URI"
  value       = var.create_key_vault ? azurerm_key_vault.this[0].vault_uri : ""
}

# ==============================================
# CMK Key Outputs
# ==============================================

output "key_id" {
  description = "CMK key ID (full versioned ID)"
  value       = local.key_id
}

output "key_version" {
  description = "CMK key version"
  value       = var.create_key_vault && var.existing_key_id == "" ? azurerm_key_vault_key.this[0].version : ""
}

output "key_name" {
  description = "CMK key name"
  value       = var.key_name
}

# ==============================================
# Configuration Outputs
# ==============================================

output "key_vault_configuration" {
  description = "Key Vault configuration summary"
  value = {
    key_vault_created     = var.create_key_vault
    key_vault_id          = local.key_vault_id
    key_id                = local.key_id
    purge_protection      = var.create_key_vault ? azurerm_key_vault.this[0].purge_protection_enabled : null
    soft_delete_enabled   = var.enable_soft_delete
    auto_rotation_enabled = var.enable_auto_rotation
    rotation_policy_days  = var.enable_auto_rotation ? var.rotation_policy_days : null
    key_type              = var.key_type
    key_size              = var.key_size
  }
}

# ==============================================
# Advanced Outputs (Full Objects)
# ==============================================

output "key_vault" {
  description = "Complete Key Vault object (for advanced use)"
  value       = var.create_key_vault ? azurerm_key_vault.this[0] : null
  sensitive   = true
}

output "key" {
  description = "Complete Key object (for advanced use)"
  value       = var.create_key_vault && var.existing_key_id == "" ? azurerm_key_vault_key.this[0] : null
  sensitive   = true
}
