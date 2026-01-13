***REMOVED*** Customer-Managed Keys (CMK) Module

> **Encrypt your workspace data** with your own Azure Key Vault encryption keys for complete control over data security.

---

***REMOVED******REMOVED*** Overview

The CMK module enables encryption of Databricks workspace data using customer-managed keys stored in Azure Key Vault. This gives you complete control over encryption keys and allows you to meet compliance requirements for key management.

***REMOVED******REMOVED******REMOVED*** What Gets Encrypted

**Three encryption scopes available:**

1. **Managed Services** - Control plane data (notebooks, secrets, queries, cluster configurations)
2. **Managed Disks** - Data plane VM disks (cluster worker node data disks)
3. **DBFS Root** - Workspace storage (DBFS root, libraries, init scripts)

***REMOVED******REMOVED******REMOVED*** Key Features

✅ **Auto-Rotation** - Keys automatically rotate every 90 days  
✅ **Flexible** - Create new Key Vault or use existing  
✅ **Comprehensive** - All three scopes supported  
✅ **Access Control** - Automatic access policy configuration  
✅ **Single Apply** - Works in one `terraform apply` for fresh deployments

---

***REMOVED******REMOVED*** Architecture

***REMOVED******REMOVED******REMOVED*** Component Overview

```
┌─────────────────────────────────────────────────────────┐
│              Azure Key Vault (Your Control)             │
│  ┌─────────────────────────────────────────────────┐   │
│  │  CMK Key (Auto-Rotation: 90 days)              │   │
│  │  ├─ Version 1                                   │   │
│  │  ├─ Version 2                                   │   │
│  │  └─ Version N (Active)                          │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  Access Policies:                                       │
│  ├─ Terraform: Full key management                     │
│  ├─ Databricks SP: Get, WrapKey, UnwrapKey            │
│  └─ DBFS Storage: Get, WrapKey, UnwrapKey             │
└─────────────────────────────────────────────────────────┘
                         │
                         │ Encrypts
                         ▼
┌─────────────────────────────────────────────────────────┐
│           Azure Databricks Workspace                     │
│  ┌────────────────────────────────────────────┐         │
│  │ 🔒 Managed Services (Notebooks, Secrets)   │         │
│  └────────────────────────────────────────────┘         │
│  ┌────────────────────────────────────────────┐         │
│  │ 🔒 Managed Disks (Cluster VM Data Disks)   │         │
│  └────────────────────────────────────────────┘         │
│  ┌────────────────────────────────────────────┐         │
│  │ 🔒 DBFS Root (Workspace Storage)           │         │
│  └────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────┘
```

***REMOVED******REMOVED******REMOVED*** How It Works

1. **Key Vault Creation** - Module creates (or uses existing) Azure Key Vault with required configuration
2. **CMK Key Generation** - Encryption key created with auto-rotation policy
3. **Access Policies** - Automatic configuration for Terraform, Databricks, and DBFS storage
4. **Workspace Configuration** - Workspace created with CMK references for each scope
5. **Data Encryption** - All data encrypted at rest with your key

---

***REMOVED******REMOVED*** Configuration

***REMOVED******REMOVED******REMOVED*** Basic Usage

Enable all three CMK scopes:

```hcl
***REMOVED*** terraform.tfvars
enable_cmk_managed_services = true  ***REMOVED*** Notebooks, secrets, queries
enable_cmk_managed_disks    = true  ***REMOVED*** Cluster VM disks
enable_cmk_dbfs_root        = true  ***REMOVED*** Workspace storage

create_key_vault = true  ***REMOVED*** Create new Key Vault
```

***REMOVED******REMOVED******REMOVED*** Option 1: Create New Key Vault (Recommended)

```hcl
create_key_vault = true

***REMOVED*** Key Vault automatically configured with:
***REMOVED*** - Purge protection: Enabled
***REMOVED*** - Soft delete: 90 days
***REMOVED*** - Key rotation: 90 days
***REMOVED*** - RBAC model: Enabled
```

***REMOVED******REMOVED******REMOVED*** Option 2: Use Existing Key Vault

```hcl
create_key_vault = false

existing_key_vault_id = "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.KeyVault/vaults/<kv-name>"
existing_key_id       = "https://<kv-name>.vault.azure.net/keys/<key-name>/<version>"  ***REMOVED*** Optional

***REMOVED*** Requirements for existing Key Vault:
***REMOVED*** - Purge protection: Must be enabled
***REMOVED*** - Soft delete: Must be enabled
***REMOVED*** - Access policies: Will be added automatically
```

***REMOVED******REMOVED******REMOVED*** Selective Scope Enablement

Enable only specific scopes:

```hcl
***REMOVED*** Example: Only encrypt managed services and DBFS
enable_cmk_managed_services = true
enable_cmk_managed_disks    = false  ***REMOVED*** Skip managed disks
enable_cmk_dbfs_root        = true
```

---

***REMOVED******REMOVED*** Module Structure

```
modules/key-vault/
├── main.tf       ***REMOVED*** Key Vault, key, access policies
├── variables.tf  ***REMOVED*** Configuration options
└── outputs.tf    ***REMOVED*** Key Vault ID, key ID, summary
```

***REMOVED******REMOVED******REMOVED*** Key Resources

- `azurerm_key_vault` - Key Vault with purge protection
- `azurerm_key_vault_key` - CMK key with rotation policy
- `azurerm_key_vault_access_policy` - Access for Terraform, Databricks, DBFS
- Integration with workspace module for encryption

---

***REMOVED******REMOVED*** Practical Usage

***REMOVED******REMOVED******REMOVED*** Deployment Workflow

**1. Configure Variables**

```hcl
***REMOVED*** Enable CMK in terraform.tfvars
enable_cmk_managed_services = true
enable_cmk_managed_disks    = true
enable_cmk_dbfs_root        = true
create_key_vault            = true
```

**2. Deploy**

```bash
terraform apply
```

**3. Verify**

```bash
terraform output customer_managed_keys
```

Expected output:
```hcl
{
  "auto_rotation_enabled" = true
  "dbfs_root"            = true
  "key_id"               = "https://...-kv-....vault.azure.net/keys/databricks-cmk/..."
  "key_vault_id"         = "/subscriptions/.../vaults/..."
  "key_vault_name"       = "proddb-kv-xxxxx"
  "managed_disks"        = true
  "managed_services"     = true
}
```

***REMOVED******REMOVED******REMOVED*** Validation Checklist

After deployment, verify:

- [ ] Key Vault created (or existing one used)
- [ ] CMK key generated with rotation policy
- [ ] Access policies configured (3 policies: Terraform, Databricks, DBFS)
- [ ] Workspace shows CMK enabled in Azure Portal
- [ ] Cluster can start successfully (validates managed disks CMK)
- [ ] Can read/write to DBFS (validates DBFS root CMK)

***REMOVED******REMOVED******REMOVED*** Testing Encryption

**Test Managed Services CMK:**
```python
***REMOVED*** Create a notebook and secret
databricks secrets create-scope --scope test-scope
databricks secrets put --scope test-scope --key test-key --string-value "encrypted"

***REMOVED*** Verify it's stored (encrypted at rest with your key)
databricks secrets list --scope test-scope
```

**Test Managed Disks CMK:**
```bash
***REMOVED*** Start a cluster - disks are automatically encrypted
***REMOVED*** Check Azure Portal → Cluster VMs → Disks → Encryption = "Customer-managed key"
```

**Test DBFS Root CMK:**
```python
***REMOVED*** Write to DBFS
dbutils.fs.put("/test.txt", "encrypted content")

***REMOVED*** Verify storage account encryption in Azure Portal
***REMOVED*** Storage Account → Encryption → "Customer-managed keys"
```

---

***REMOVED******REMOVED*** How-To Guides

***REMOVED******REMOVED******REMOVED*** Rotate Keys Manually

Keys auto-rotate, but you can manually rotate if needed:

```bash
***REMOVED*** Azure CLI
az keyvault key rotate \
  --vault-name <key-vault-name> \
  --name databricks-cmk
```

***REMOVED******REMOVED******REMOVED*** Update Key Version

```bash
***REMOVED*** Get latest key version
az keyvault key show \
  --vault-name <key-vault-name> \
  --name databricks-cmk \
  --query "key.kid"

***REMOVED*** Update in terraform.tfvars (if using existing key)
existing_key_id = "https://<kv>.vault.azure.net/keys/databricks-cmk/<new-version>"

terraform apply
```

***REMOVED******REMOVED******REMOVED*** Disable CMK (Not Recommended)

⚠️ **Warning**: Cannot disable CMK once enabled. You must destroy and recreate workspace.

---

***REMOVED******REMOVED*** Troubleshooting

***REMOVED******REMOVED******REMOVED*** Issue: "Storage account identity is empty"

**Cause**: Workspace not configured for CMK infrastructure.

**Solution**: Ensure `customer_managed_key_enabled = true` is set on workspace.

***REMOVED******REMOVED******REMOVED*** Issue: "Authentication issue on keyvault"

**Cause**: DBFS storage account missing access policy.

**Solution**: Check `azurerm_key_vault_access_policy.dbfs_storage` exists.

***REMOVED******REMOVED******REMOVED*** Issue: Workspace destroy fails

**Cause**: Key Vault still in use.

**Solution**: Module handles this automatically via `depends_on` ordering.

---

***REMOVED******REMOVED*** Best Practices

✅ **DO:**
- Enable all three scopes for comprehensive encryption
- Use auto-rotation (90-day default)
- Set `create_key_vault = true` for new deployments
- Enable purge protection on Key Vault
- Tag Key Vault appropriately

❌ **DON'T:**
- Disable purge protection on Key Vault
- Share Key Vault across multiple workspaces
- Delete Key Vault before workspace
- Manually modify access policies created by Terraform

---

***REMOVED******REMOVED*** Cost Considerations

- **Key Vault**: ~$0.03/month per vault
- **CMK Operations**: ~$0.03 per 10,000 operations
- **Key Rotations**: Included (no extra cost)

**Typical monthly cost**: < $5 for standard usage

---

***REMOVED******REMOVED*** References

**Azure Documentation:**
- [CMK for Managed Services](https://learn.microsoft.com/en-us/azure/databricks/security/keys/cmk-managed-services-azure/)
- [CMK for Managed Disks](https://learn.microsoft.com/en-us/azure/databricks/security/keys/cmk-managed-disks-azure/)
- [Azure Key Vault](https://learn.microsoft.com/en-us/azure/key-vault/)

**Terraform Providers:**
- [azurerm_key_vault](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/key_vault)
- [azurerm_databricks_workspace](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/databricks_workspace)
- [azurerm_databricks_workspace_root_dbfs_customer_managed_key](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/databricks_workspace_root_dbfs_customer_managed_key)

**Related Guides:**
- [CMK Configuration Guide](../guides/02-CMK-CONFIGURATION.md)
- [Workspace Module](02-WORKSPACE.md)
- [Troubleshooting](../04-TROUBLESHOOTING.md)
