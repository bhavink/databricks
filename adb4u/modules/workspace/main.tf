***REMOVED*** ==============================================
***REMOVED*** Azure Databricks Workspace
***REMOVED*** ==============================================

resource "azurerm_databricks_workspace" "this" {
  name                        = var.workspace_name
  resource_group_name         = var.resource_group_name
  location                    = var.location
  sku                         = "premium"  ***REMOVED*** Required for Unity Catalog
  managed_resource_group_name = "${var.workspace_prefix}-managed-rg"

  ***REMOVED*** Public network access control
  ***REMOVED*** - true: Allows public internet access (needed for initial deployment from outside VNet)
  ***REMOVED*** - false: Forces Private Link only (air-gapped, requires VPN/Bastion/Jump Box access)
  public_network_access_enabled = var.enable_public_network_access
  
  ***REMOVED*** Network Security Policy: Full Private requires Private Link
  network_security_group_rules_required = var.enable_private_link ? "NoAzureDatabricksRules" : "AllRules"

  ***REMOVED*** Customer-Managed Keys (CMK) - Enable flag required for storage_account_identity
  ***REMOVED*** This flag must be enabled if ANY CMK feature is used (Managed Services or DBFS Root)
  ***REMOVED*** See: https://github.com/hashicorp/terraform-provider-azurerm/blob/main/examples/databricks/customer-managed-key/dbfs/main.tf
  customer_managed_key_enabled = var.enable_cmk_managed_services || var.enable_cmk_dbfs_root ? true : false
  
  ***REMOVED*** Customer-Managed Keys (CMK) for Managed Services
  ***REMOVED*** Encrypts notebooks, secrets, queries stored in control plane
  ***REMOVED*** See: https://github.com/hashicorp/terraform-provider-azurerm/blob/main/examples/databricks/customer-managed-key/managed-services/main.tf
  managed_services_cmk_key_vault_key_id = var.enable_cmk_managed_services ? var.cmk_key_vault_key_id : null
  
  ***REMOVED*** Customer-Managed Keys (CMK) for Managed Disks
  ***REMOVED*** Encrypts cluster VM managed disks (data disks only, not OS disks)
  ***REMOVED*** See: https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/databricks_workspace
  managed_disk_cmk_key_vault_key_id = var.enable_cmk_managed_disks ? var.cmk_key_vault_key_id : null
  managed_disk_cmk_rotation_to_latest_version_enabled = var.enable_cmk_managed_disks ? true : null
  
  ***REMOVED*** VNet injection with Secure Cluster Connectivity (NPIP)
  custom_parameters {
    ***REMOVED*** NPIP/SCC always enabled - no public IPs on cluster VMs
    no_public_ip = true

    ***REMOVED*** Network configuration
    public_subnet_name  = var.public_subnet_name
    private_subnet_name = var.private_subnet_name
    virtual_network_id  = var.vnet_id

    ***REMOVED*** NSG associations
    public_subnet_network_security_group_association_id  = var.public_subnet_nsg_association_id
    private_subnet_network_security_group_association_id = var.private_subnet_nsg_association_id
    
    ***REMOVED*** Custom DBFS storage name (Full Private pattern only)
    storage_account_name = var.dbfs_storage_name != "" ? var.dbfs_storage_name : null
  }

  ***REMOVED*** Dependency: Key Vault access must be configured before workspace creation
  ***REMOVED*** This is handled by the deployment layer with depends_on
  
  tags = var.tags
  
  lifecycle {
    ignore_changes = [
      ***REMOVED*** Databricks manages these automatically in certain scenarios
      custom_parameters[0].storage_account_name
    ]
  }
}

***REMOVED*** ==============================================
***REMOVED*** Data Source: DBFS Storage Account
***REMOVED*** ==============================================

***REMOVED*** Retrieve DBFS storage account created by Databricks in the managed resource group
***REMOVED*** Note: This data source will be read during apply, after workspace creation
data "azurerm_resources" "dbfs_storage" {
  type                = "Microsoft.Storage/storageAccounts"
  resource_group_name = azurerm_databricks_workspace.this.managed_resource_group_name

  depends_on = [azurerm_databricks_workspace.this]
}

***REMOVED*** ==============================================
***REMOVED*** DBFS Root Storage CMK Encryption
***REMOVED*** ==============================================

***REMOVED*** Key Vault Access Policy for DBFS Storage Account Identity
***REMOVED*** This is required for DBFS CMK to work - the storage account's managed identity needs access to the Key Vault
***REMOVED*** Note: storage_account_identity is created when customer_managed_key_enabled = true on the workspace
***REMOVED*** See: https://github.com/hashicorp/terraform-provider-azurerm/blob/main/examples/databricks/customer-managed-key/dbfs/main.tf
resource "azurerm_key_vault_access_policy" "dbfs_storage" {
  count = var.enable_cmk_dbfs_root ? 1 : 0

  key_vault_id = var.cmk_key_vault_id
  tenant_id    = azurerm_databricks_workspace.this.storage_account_identity[0].tenant_id
  object_id    = azurerm_databricks_workspace.this.storage_account_identity[0].principal_id

  key_permissions = [
    "Get",
    "UnwrapKey",
    "WrapKey",
  ]

  depends_on = [
    azurerm_databricks_workspace.this
  ]
}

***REMOVED*** Customer-Managed Key for DBFS root storage account
***REMOVED*** This resource applies CMK encryption to the workspace DBFS root storage
***REMOVED*** See: https://github.com/hashicorp/terraform-provider-azurerm/blob/main/examples/databricks/customer-managed-key/dbfs/main.tf
resource "azurerm_databricks_workspace_root_dbfs_customer_managed_key" "this" {
  count = var.enable_cmk_dbfs_root ? 1 : 0

  workspace_id     = azurerm_databricks_workspace.this.id
  key_vault_key_id = var.cmk_key_vault_key_id

  depends_on = [
    azurerm_key_vault_access_policy.dbfs_storage
  ]
}

***REMOVED*** ==============================================
***REMOVED*** Managed Disks CMK Encryption
***REMOVED*** ==============================================

***REMOVED*** Data source to find Disk Encryption Set (DES) created by Azure
***REMOVED*** When managed_disk_cmk is enabled, Azure automatically creates a DES in the managed resource group
***REMOVED*** We need to find it by querying the resources in the managed RG
***REMOVED*** Reference: https://learn.microsoft.com/en-us/azure/databricks/security/keys/customer-managed-keys-managed-services-azure
data "azurerm_resources" "disk_encryption_set" {
  count               = var.enable_cmk_managed_disks ? 1 : 0
  type                = "Microsoft.Compute/diskEncryptionSets"
  resource_group_name = azurerm_databricks_workspace.this.managed_resource_group_name

  depends_on = [azurerm_databricks_workspace.this]
}

***REMOVED*** Data source to read the actual Disk Encryption Set details including identity
***REMOVED*** The azurerm_resources data source only gives us the ID, we need the specific DES data source for identity
data "azurerm_disk_encryption_set" "this" {
  count               = var.enable_cmk_managed_disks ? 1 : 0
  name                = split("/", data.azurerm_resources.disk_encryption_set[0].resources[0].id)[8]
  resource_group_name = azurerm_databricks_workspace.this.managed_resource_group_name

  depends_on = [
    azurerm_databricks_workspace.this,
    data.azurerm_resources.disk_encryption_set
  ]
}

***REMOVED*** Key Vault Access Policy for Disk Encryption Set Managed Identity
***REMOVED*** This grants the DES permission to use the CMK for encrypting managed disks
***REMOVED*** Without this, cluster startup will fail with: KeyVaultAccessForbidden
resource "azurerm_key_vault_access_policy" "disk_encryption_set" {
  count = var.enable_cmk_managed_disks ? 1 : 0

  key_vault_id = var.cmk_key_vault_id
  tenant_id    = data.azurerm_disk_encryption_set.this[0].identity[0].tenant_id
  object_id    = data.azurerm_disk_encryption_set.this[0].identity[0].principal_id

  key_permissions = [
    "Get",
    "WrapKey",
    "UnwrapKey",
  ]

  depends_on = [
    azurerm_databricks_workspace.this,
    data.azurerm_disk_encryption_set.this
  ]
}

***REMOVED*** ==============================================
***REMOVED*** Workspace Configuration (Optional Features)
***REMOVED*** ==============================================

***REMOVED*** Configure workspace settings via Databricks provider
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

***REMOVED*** ==============================================
***REMOVED*** IP Access Lists (Optional)
***REMOVED*** ==============================================

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
