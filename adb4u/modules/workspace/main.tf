# ==============================================
# Azure Databricks Workspace
# ==============================================

resource "azurerm_databricks_workspace" "this" {
  name                        = var.workspace_name
  resource_group_name         = var.resource_group_name
  location                    = var.location
  sku                         = "premium"  # Required for Unity Catalog
  managed_resource_group_name = "${var.workspace_prefix}-managed-rg"

  # Public network access control
  # Non-PL: public_network_access_enabled = true (default)
  # Full Private: public_network_access_enabled = false (forces Private Link)
  public_network_access_enabled = !var.enable_private_link
  
  # Network Security Policy: Full Private requires Private Link
  network_security_group_rules_required = var.enable_private_link ? "NoAzureDatabricksRules" : "AllRules"

  # Customer-Managed Keys (CMK) for Managed Services
  # Encrypts notebooks, secrets, queries stored in control plane
  customer_managed_key_enabled = var.enable_cmk_managed_services
  
  # VNet injection with Secure Cluster Connectivity (NPIP)
  custom_parameters {
    # NPIP/SCC always enabled - no public IPs on cluster VMs
    no_public_ip = true

    # Network configuration
    public_subnet_name  = var.public_subnet_name
    private_subnet_name = var.private_subnet_name
    virtual_network_id  = var.vnet_id

    # NSG associations
    public_subnet_network_security_group_association_id  = var.public_subnet_nsg_association_id
    private_subnet_network_security_group_association_id = var.private_subnet_nsg_association_id
  }

  tags = var.tags
}

# ==============================================
# Customer-Managed Keys for Managed Disks
# ==============================================

# Disk Encryption Set for cluster VM managed disks
# This is required for CMK encryption of compute resources
resource "azurerm_disk_encryption_set" "this" {
  count = var.enable_cmk_managed_disks && var.cmk_key_vault_key_id != "" ? 1 : 0
  
  name                = "${var.workspace_prefix}-des"
  resource_group_name = var.resource_group_name
  location            = var.location
  key_vault_key_id    = var.cmk_key_vault_key_id
  
  identity {
    type = "SystemAssigned"
  }
  
  tags = var.tags
}

# Grant Disk Encryption Set access to Key Vault
resource "azurerm_key_vault_access_policy" "des" {
  count = var.enable_cmk_managed_disks && var.cmk_key_vault_key_id != "" ? 1 : 0
  
  key_vault_id = var.cmk_key_vault_id
  tenant_id    = azurerm_disk_encryption_set.this[0].identity[0].tenant_id
  object_id    = azurerm_disk_encryption_set.this[0].identity[0].principal_id
  
  key_permissions = [
    "Get",
    "WrapKey",
    "UnwrapKey"
  ]
  
  depends_on = [
    azurerm_disk_encryption_set.this
  ]
}

# ==============================================
# Workspace Configuration (Optional Features)
# ==============================================

# Configure workspace settings via Databricks provider
resource "databricks_workspace_conf" "this" {
  count = var.enable_ip_access_lists || length(var.additional_workspace_config) > 0 ? 1 : 0

  custom_config = merge(
    {
      "enableIpAccessLists" = var.enable_ip_access_lists ? "true" : "false"
    },
    var.additional_workspace_config
  )

  depends_on = [
    azurerm_databricks_workspace.this
  ]
}

# ==============================================
# IP Access Lists (Optional)
# ==============================================

resource "databricks_ip_access_list" "allowed" {
  count = var.enable_ip_access_lists ? length(var.allowed_ip_ranges) : 0

  list_type    = "ALLOW"
  ip_addresses = [var.allowed_ip_ranges[count.index]]
  label        = "Allowed IP range ${count.index + 1}"
  enabled      = true

  depends_on = [
    databricks_workspace_conf.this
  ]
}
