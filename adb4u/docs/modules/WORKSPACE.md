***REMOVED*** Workspace Module

**Module**: `modules/workspace`  
**Purpose**: Creates and configures Azure Databricks workspace with security features

---

***REMOVED******REMOVED*** Overview

The workspace module creates a fully configured Azure Databricks workspace with support for Private Link, Customer-Managed Keys (CMK), IP Access Lists, and Secure Cluster Connectivity (NPIP).

***REMOVED******REMOVED******REMOVED*** Key Features

- ✅ **VNet Injection**: Deploy into customer-managed VNet
- ✅ **Secure Cluster Connectivity (NPIP)**: Always enabled (no public IPs on clusters)
- ✅ **Private Link**: Optional front-end and back-end isolation
- ✅ **Customer-Managed Keys**: Optional encryption for managed services, disks, and DBFS
- ✅ **IP Access Lists**: Optional workspace access restrictions
- ✅ **Production-Ready**: Battle-tested configurations

---

***REMOVED******REMOVED*** Architecture

***REMOVED******REMOVED******REMOVED*** Workspace Components

```
┌──────────────────────────────────────────────────────────────┐
│ Azure Databricks Workspace                                   │
│                                                              │
│  Control Plane (Managed by Databricks)                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ - Web UI / Notebooks                                   │ │
│  │ - Cluster Manager                                      │ │
│  │ - Jobs Scheduler                                       │ │
│  │ - Secrets (encrypted with CMK if enabled)             │ │
│  └────────────────────────────────────────────────────────┘ │
│           │                                                  │
│           ↓                                                  │
│  Data Plane (Customer VNet - VNet Injection)                │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Public Subnet          │  Private Subnet               │ │
│  │ - Driver Nodes         │  - Worker Nodes               │ │
│  │ - No Public IPs (NPIP) │  - No Public IPs (NPIP)       │ │
│  │ - Managed Disks (CMK)  │  - Managed Disks (CMK)        │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  Managed Storage                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ DBFS Root Storage (CMK optional)                       │ │
│  │ - Workspace files                                      │ │
│  │ - Cluster logs                                         │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

***REMOVED******REMOVED*** Resources Created

| Resource Type | Name Pattern | Purpose |
|--------------|--------------|---------|
| `azurerm_databricks_workspace` | `{workspace_name}` | Main workspace resource |
| `azurerm_disk_encryption_set` | `{prefix}-des` | Disk encryption (if CMK enabled) |
| `azurerm_key_vault_access_policy` | (auto) | DES access to Key Vault (if CMK enabled) |
| `databricks_workspace_conf` | (auto) | DBFS CMK configuration (if enabled) |

**Managed Resources** (created by Databricks):
- Managed resource group (`databricks-rg-{workspace}-{random}`)
- Storage account for DBFS root
- Network security group (if Non-PL)
- Cluster VMs and managed disks

---

***REMOVED******REMOVED*** Variables

***REMOVED******REMOVED******REMOVED*** Workspace Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `workspace_name` | string | (required) | Databricks workspace name |
| `workspace_prefix` | string | (required) | Naming prefix for managed resources |
| `resource_group_name` | string | (required) | Resource group for workspace |
| `location` | string | (required) | Azure region |

***REMOVED******REMOVED******REMOVED*** Network Configuration

| Variable | Type | Description |
|----------|------|-------------|
| `vnet_id` | string | Virtual Network ID for VNet injection |
| `public_subnet_name` | string | Public/host subnet name |
| `private_subnet_name` | string | Private/container subnet name |
| `public_subnet_nsg_association_id` | string | Public subnet NSG association |
| `private_subnet_nsg_association_id` | string | Private subnet NSG association |
| `enable_private_link` | bool | Enable Private Link (default: `false`) |

**Private Link Effect**:
- `true`: Control plane + data plane use Private Link, `public_network_access_enabled = false`
- `false`: Control plane public, data plane private (NPIP)

***REMOVED******REMOVED******REMOVED*** Customer-Managed Keys (CMK)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `enable_cmk_managed_services` | bool | `false` | Encrypt control plane data (notebooks, secrets, queries) |
| `enable_cmk_managed_disks` | bool | `false` | Encrypt cluster VM managed disks |
| `enable_cmk_dbfs_root` | bool | `false` | Encrypt workspace DBFS root storage |
| `cmk_key_vault_key_id` | string | `""` | Key Vault key ID (required if any CMK enabled) |
| `cmk_key_vault_id` | string | `""` | Key Vault ID (required for managed disks CMK) |
| `databricks_account_id` | string | `""` | Databricks account ID (required for CMK) |

**CMK Scope**:

| Encryption Target | Variable | What's Encrypted |
|------------------|----------|------------------|
| **Managed Services** | `enable_cmk_managed_services` | Notebooks, secrets, queries, job results |
| **Managed Disks** | `enable_cmk_managed_disks` | Cluster VM OS and data disks |
| **DBFS Root** | `enable_cmk_dbfs_root` | Workspace storage (logs, libraries, init scripts) |

**Cost Impact**: No additional cost for CMK (Azure Disk Encryption)

***REMOVED******REMOVED******REMOVED*** IP Access Lists

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `enable_ip_access_lists` | bool | `false` | Enable workspace IP restrictions |
| `allowed_ip_ranges` | list(string) | `[]` | Allowed CIDR ranges (e.g., `["203.0.113.0/24"]`) |

**Use Cases**:
- Restrict access to corporate network ranges
- Compliance requirements
- Additional security layer

**Important**: Does not apply to Private Link workspaces (already isolated)

***REMOVED******REMOVED******REMOVED*** Additional Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `additional_workspace_config` | map(string) | `{}` | Additional workspace settings (key-value) |
| `tags` | map(string) | `{}` | Tags for workspace resource |

---

***REMOVED******REMOVED*** Outputs

| Output | Description |
|--------|-------------|
| `workspace_id` | Full Azure resource ID |
| `workspace_id_numeric` | Numeric workspace ID (for Unity Catalog) |
| `workspace_url` | Workspace URL (e.g., `https://adb-123.azuredatabricks.net`) |
| `workspace_name` | Workspace name |
| `managed_resource_group_name` | Name of Databricks-managed resource group |
| `disk_encryption_set_id` | Disk Encryption Set ID (if CMK enabled) |

---

***REMOVED******REMOVED*** Secure Cluster Connectivity (NPIP)

***REMOVED******REMOVED******REMOVED*** Always Enabled

This module **always** enables NPIP (Secure Cluster Connectivity):

```hcl
custom_parameters {
  no_public_ip = true  ***REMOVED*** NPIP - Always enabled
}
```

**Benefits**:
- ✅ No public IPs on cluster VMs
- ✅ All traffic stays within VNet
- ✅ Reduced attack surface
- ✅ Compliance-friendly

**NSG Rule Management**:
- **Non-PL**: Databricks manages NSG rules automatically
- **Private Link**: Custom NSG rules required (handled by networking module)

---

***REMOVED******REMOVED*** Customer-Managed Keys (CMK)

***REMOVED******REMOVED******REMOVED*** CMK Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Azure Key Vault (Customer-Owned)                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ CMK Key (RSA 2048)                                   │  │
│  │ - Auto-rotation enabled (90 days)                    │  │
│  │ - Premium SKU (required)                             │  │
│  │ - Purge protection enabled                           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Databricks Workspace                                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Managed Services (if enabled)                        │  │
│  │ - Notebooks (encrypted)                              │  │
│  │ - Secrets (encrypted)                                │  │
│  │ - Query results (encrypted)                          │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Managed Disks (if enabled)                           │  │
│  │ - Cluster VM OS disks (encrypted)                    │  │
│  │ - Cluster VM data disks (encrypted)                  │  │
│  │ - Disk Encryption Set manages keys                   │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ DBFS Root Storage (if enabled)                       │  │
│  │ - Workspace files (encrypted)                        │  │
│  │ - Cluster logs (encrypted)                           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

***REMOVED******REMOVED******REMOVED*** CMK Implementation

**Managed Services CMK**:
```hcl
customer_managed_key_enabled = true

managed_services_customer_managed_key {
  key_vault_key_id = var.cmk_key_vault_key_id
}
```

**Managed Disks CMK**:
```hcl
managed_disk_customer_managed_key {
  key_vault_key_id = var.cmk_key_vault_key_id
}

***REMOVED*** Disk Encryption Set
resource "azurerm_disk_encryption_set" "this" {
  key_vault_key_id = var.cmk_key_vault_key_id
  ***REMOVED*** Automatic key rotation supported
}
```

**DBFS Root CMK**:
```hcl
resource "databricks_workspace_conf" "dbfs_cmk" {
  custom_config = {
    "azure_kms_key_vault_url" = var.cmk_key_vault_key_id
  }
}
```

***REMOVED******REMOVED******REMOVED*** CMK Requirements

1. **Key Vault**:
   - Premium SKU (required for CMK)
   - Purge protection enabled
   - Soft delete enabled (7+ days)

2. **Key Vault Key**:
   - RSA 2048 or 3072
   - Auto-rotation enabled (recommended)
   - Backup enabled

3. **Permissions**:
   - Databricks service principal: `Get`, `WrapKey`, `UnwrapKey`
   - Disk Encryption Set: `Get`, `WrapKey`, `UnwrapKey`

---

***REMOVED******REMOVED*** Usage Examples

***REMOVED******REMOVED******REMOVED*** Example 1: Non-PL Workspace (Minimal)

```hcl
module "workspace" {
  source = "../../modules/workspace"
  
  workspace_name      = "prod-workspace"
  workspace_prefix    = "proddb"
  resource_group_name = azurerm_resource_group.this.name
  location            = "eastus2"
  
  ***REMOVED*** Network configuration
  vnet_id                           = module.networking.vnet_id
  public_subnet_name                = module.networking.public_subnet_name
  private_subnet_name               = module.networking.private_subnet_name
  public_subnet_nsg_association_id  = module.networking.public_subnet_nsg_association_id
  private_subnet_nsg_association_id = module.networking.private_subnet_nsg_association_id
  
  ***REMOVED*** Non-PL configuration (defaults)
  enable_private_link = false
  
  tags = {
    Environment = "Production"
  }
}
```

***REMOVED******REMOVED******REMOVED*** Example 2: Private Link Workspace

```hcl
module "workspace" {
  source = "../../modules/workspace"
  
  workspace_name      = "private-workspace"
  workspace_prefix    = "privdb"
  resource_group_name = azurerm_resource_group.this.name
  location            = "eastus2"
  
  ***REMOVED*** Network configuration
  vnet_id                           = module.networking.vnet_id
  public_subnet_name                = module.networking.public_subnet_name
  private_subnet_name               = module.networking.private_subnet_name
  public_subnet_nsg_association_id  = module.networking.public_subnet_nsg_association_id
  private_subnet_nsg_association_id = module.networking.private_subnet_nsg_association_id
  
  ***REMOVED*** Private Link enabled
  enable_private_link = true
  
  tags = {
    Environment = "Production"
    Connectivity = "PrivateLink"
  }
}
```

***REMOVED******REMOVED******REMOVED*** Example 3: Workspace with Full CMK

```hcl
module "workspace" {
  source = "../../modules/workspace"
  
  workspace_name      = "cmk-workspace"
  workspace_prefix    = "cmkdb"
  resource_group_name = azurerm_resource_group.this.name
  location            = "eastus2"
  
  ***REMOVED*** Network configuration
  vnet_id                           = module.networking.vnet_id
  public_subnet_name                = module.networking.public_subnet_name
  private_subnet_name               = module.networking.private_subnet_name
  public_subnet_nsg_association_id  = module.networking.public_subnet_nsg_association_id
  private_subnet_nsg_association_id = module.networking.private_subnet_nsg_association_id
  
  ***REMOVED*** CMK enabled for all three scopes
  enable_cmk_managed_services = true
  enable_cmk_managed_disks    = true
  enable_cmk_dbfs_root        = true
  cmk_key_vault_key_id        = module.key_vault.key_id
  cmk_key_vault_id            = module.key_vault.key_vault_id
  databricks_account_id       = var.databricks_account_id
  
  tags = {
    Environment = "Production"
    Encryption  = "CMK"
  }
}
```

***REMOVED******REMOVED******REMOVED*** Example 4: Workspace with IP Access Lists

```hcl
module "workspace" {
  source = "../../modules/workspace"
  
  workspace_name      = "ip-restricted-workspace"
  workspace_prefix    = "securedb"
  resource_group_name = azurerm_resource_group.this.name
  location            = "eastus2"
  
  ***REMOVED*** Network configuration
  vnet_id                           = module.networking.vnet_id
  public_subnet_name                = module.networking.public_subnet_name
  private_subnet_name               = module.networking.private_subnet_name
  public_subnet_nsg_association_id  = module.networking.public_subnet_nsg_association_id
  private_subnet_nsg_association_id = module.networking.private_subnet_nsg_association_id
  
  ***REMOVED*** IP Access Lists
  enable_ip_access_lists = true
  allowed_ip_ranges = [
    "203.0.113.0/24",    ***REMOVED*** Corporate office
    "198.51.100.0/24",   ***REMOVED*** Remote office
  ]
  
  tags = {
    Environment = "Production"
    Security    = "IPRestricted"
  }
}
```

---

***REMOVED******REMOVED*** Best Practices

***REMOVED******REMOVED******REMOVED*** Security

1. **CMK Strategy**
   - Enable for compliance requirements
   - Use auto-rotation (90 days recommended)
   - Test key rotation in dev first
   - Monitor Key Vault access logs

2. **IP Access Lists**
   - Document allowed ranges
   - Use narrowest CIDR possible
   - Regularly review and update
   - Combine with conditional access policies

3. **Private Link**
   - Use for highly regulated workloads
   - Requires DNS configuration
   - Plan for increased cost (~$40/month)

***REMOVED******REMOVED******REMOVED*** Cost Optimization

| Feature | Monthly Cost | When to Enable |
|---------|-------------|----------------|
| Workspace (base) | $0 | Always |
| Private Link | ~$40 | Compliance required |
| CMK | $0 | Compliance required |
| NPIP | $0 | Always (enabled by default) |

***REMOVED******REMOVED******REMOVED*** Naming Conventions

```hcl
workspace_name = "${var.environment}-${var.workload}-workspace"
***REMOVED*** Examples:
***REMOVED*** - prod-analytics-workspace
***REMOVED*** - dev-ml-workspace
***REMOVED*** - staging-etl-workspace
```

---

***REMOVED******REMOVED*** Troubleshooting

***REMOVED******REMOVED******REMOVED*** Issue: Workspace Creation Fails (NSG Association)

**Error**:
```
Error waiting for Databricks Workspace to become ready: Future***REMOVED***WaitForCompletion
```

**Solution**: Ensure NSG associations exist before workspace creation. Module uses `depends_on`:
```hcl
depends_on = [
  var.public_subnet_nsg_association_id,
  var.private_subnet_nsg_association_id,
]
```

***REMOVED******REMOVED******REMOVED*** Issue: CMK Key Not Found

**Error**:
```
Error: Key Vault Key not found
```

**Solution**:
1. Verify `cmk_key_vault_key_id` is correct
2. Ensure service principal has `Get` permission
3. Check Key Vault firewall rules allow Databricks

***REMOVED******REMOVED******REMOVED*** Issue: IP Access List Blocks Access

**Symptom**: Cannot access workspace UI

**Solution**:
1. Check your current public IP: `curl ifconfig.me`
2. Verify IP is in `allowed_ip_ranges`
3. Temporarily disable: `enable_ip_access_lists = false`
4. Update allowed ranges and re-enable

---

***REMOVED******REMOVED*** References

- [Azure Databricks Workspace Configuration](https://learn.microsoft.com/en-us/azure/databricks/administration-guide/workspace-settings/)
- [Secure Cluster Connectivity (NPIP)](https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/secure-cluster-connectivity)
- [Customer-Managed Keys](https://learn.microsoft.com/en-us/azure/databricks/security/keys/customer-managed-keys)
- [IP Access Lists](https://learn.microsoft.com/en-us/azure/databricks/security/network/front-end/ip-access-list)
- [Private Link](https://learn.microsoft.com/en-us/azure/databricks/administration-guide/cloud-configurations/azure/private-link)

---

**Module Version**: 1.0  
**Last Updated**: 2026-01-10  
**Terraform Version**: >= 1.5
