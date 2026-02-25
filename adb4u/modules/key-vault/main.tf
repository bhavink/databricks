# ==============================================
# Data Sources
# ==============================================

# Get current client configuration
data "azurerm_client_config" "current" {}

# Get Azure Databricks Resource Provider
# This principal needs access to the Key Vault for CMK
data "azuread_service_principal" "databricks" {
  count        = var.create_key_vault ? 1 : 0
  display_name = "AzureDatabricks"
}

# ==============================================
# Local Variables
# ==============================================

locals {
  key_vault_name = var.create_key_vault ? (
    var.key_vault_name != "" ? var.key_vault_name : "${var.workspace_prefix}-kv-${random_string.suffix[0].result}"
  ) : ""

  key_vault_id = var.create_key_vault ? azurerm_key_vault.this[0].id : var.existing_key_vault_id

  # Use existing key or create new
  key_id = var.existing_key_id != "" ? var.existing_key_id : azurerm_key_vault_key.this[0].id

  # Databricks principal ID for Key Vault access
  databricks_principal_id = var.databricks_principal_id != "" ? var.databricks_principal_id : (
    var.create_key_vault ? data.azuread_service_principal.databricks[0].object_id : ""
  )
}

# ==============================================
# Random Suffix for Unique Naming
# ==============================================

resource "random_string" "suffix" {
  count   = var.create_key_vault ? 1 : 0
  length  = 6
  special = false
  upper   = false
}

# ==============================================
# Azure Key Vault
# ==============================================

resource "azurerm_key_vault" "this" {
  count = var.create_key_vault ? 1 : 0

  name                = local.key_vault_name
  location            = var.location
  resource_group_name = var.resource_group_name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard" # Use "premium" for HSM-backed keys

  # Soft delete and purge protection (required for CMK in production)
  soft_delete_retention_days  = var.soft_delete_retention_days
  purge_protection_enabled    = var.enable_purge_protection
  enabled_for_disk_encryption = true # Required for managed disk CMK
  enabled_for_deployment      = false

  # Network configuration (allow Azure services)
  network_acls {
    bypass         = "AzureServices"
    default_action = "Allow" # Change to "Deny" with specific IP rules in production
  }

  tags = merge(
    var.tags,
    {
      Purpose = "Databricks-CMK"
    }
  )
}

# ==============================================
# Key Vault Access Policy - Current User/SP
# ==============================================

resource "azurerm_key_vault_access_policy" "terraform" {
  count = var.create_key_vault ? 1 : 0

  key_vault_id = azurerm_key_vault.this[0].id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  key_permissions = [
    "Create",
    "Delete",
    "Get",
    "List",
    "Update",
    "Purge",
    "Recover",
    "GetRotationPolicy",
    "SetRotationPolicy"
  ]

  secret_permissions = [
    "Get",
    "List",
    "Set",
    "Delete",
    "Purge",
    "Recover"
  ]
}

# ==============================================
# Key Vault Access Policy - Azure Databricks
# ==============================================

resource "azurerm_key_vault_access_policy" "databricks" {
  count = var.create_key_vault ? 1 : 0

  key_vault_id = azurerm_key_vault.this[0].id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = var.databricks_principal_id != "" ? var.databricks_principal_id : data.azuread_service_principal.databricks[0].object_id

  # Permissions required for Databricks CMK
  key_permissions = [
    "Get",
    "WrapKey",
    "UnwrapKey"
  ]

  depends_on = [
    azurerm_key_vault_access_policy.terraform
  ]
}

# ==============================================
# CMK Key for Databricks
# ==============================================

resource "azurerm_key_vault_key" "this" {
  count = var.create_key_vault && var.existing_key_id == "" ? 1 : 0

  name         = var.key_name
  key_vault_id = azurerm_key_vault.this[0].id
  key_type     = var.key_type
  key_size     = var.key_type == "RSA" || var.key_type == "RSA-HSM" ? var.key_size : null
  key_opts     = var.key_opts

  # Optional expiration
  expiration_date = var.expiry_days != null ? timeadd(timestamp(), "${var.expiry_days * 24}h") : null

  # Rotation policy (auto-rotation)
  dynamic "rotation_policy" {
    for_each = var.enable_auto_rotation ? [1] : []

    content {
      automatic {
        time_before_expiry = "P30D" # Rotate 30 days before expiry
      }

      expire_after         = "P${var.rotation_policy_days}D"
      notify_before_expiry = "P10D" # Notify 10 days before expiry
    }
  }

  tags = merge(
    var.tags,
    {
      Purpose = "Databricks-CMK"
    }
  )

  depends_on = [
    azurerm_key_vault_access_policy.terraform,
    azurerm_key_vault_access_policy.databricks
  ]
}
