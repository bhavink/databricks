# Unity Catalog Module

**Module**: `modules/unity-catalog`  
**Purpose**: Creates and configures Unity Catalog metastore, storage, and external locations

---

## Overview

The Unity Catalog module provides a complete Unity Catalog implementation with support for new or existing metastores, flexible Access Connector strategies, and configurable storage connectivity (Service Endpoints vs. Private Link).

### Key Features

- ✅ **Flexible Metastore**: Create new or use existing
- ✅ **Per-Workspace External Location**: Dedicated storage per workspace
- ✅ **Access Connector**: Managed identity for Unity Catalog
- ✅ **Storage Connectivity**: Service Endpoints (default) or Private Link (optional)
- ✅ **Regional Scope**: One metastore per region, shared across workspaces
- ✅ **Clean Destroy**: `force_destroy = true` for metastores
- ✅ **Production-Ready**: RBAC, network rules, and best practices

---

## Architecture

### Unity Catalog Components

```
┌─────────────────────────────────────────────────────────────────┐
│ Databricks Account (Account-Level)                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Unity Catalog Metastore (one per region)                  │  │
│  │ - Region: eastus2                                         │  │
│  │ - Storage Root: abfss://metastore@{storage}.dfs...        │  │
│  │ - force_destroy: true (for clean destroy)                 │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ Workspace-Level Resources                                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Metastore Assignment                                      │  │
│  │ - Links workspace to metastore                            │  │
│  │ - Default metastore for workspace                         │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ External Location                                         │  │
│  │ - Per-workspace storage                                   │  │
│  │ - abfss://external@{storage}.dfs...                       │  │
│  │ - Storage Credential attached                             │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Storage Credential                                        │  │
│  │ - Uses Access Connector managed identity                 │  │
│  │ - RBAC: Storage Blob Data Contributor                     │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ Azure Storage Accounts                                           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Metastore Root Storage (ADLS Gen2)                        │  │
│  │ - Hierarchical Namespace enabled                          │  │
│  │ - Container: "metastore"                                  │  │
│  │ - Network: Service Endpoints or Private Link              │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ External Location Storage (ADLS Gen2)                     │  │
│  │ - Hierarchical Namespace enabled                          │  │
│  │ - Container: "external"                                   │  │
│  │ - Per-workspace isolation                                 │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ Access Connector (Managed Identity)                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ - System-assigned managed identity                        │  │
│  │ - RBAC assignments to storage accounts                    │  │
│  │ - Used by Storage Credentials                             │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Resources Created

| Resource Type | Name Pattern | Purpose | Scope |
|--------------|--------------|---------|-------|
| `databricks_metastore` | `{metastore_name}` | Unity Catalog metastore | Account |
| `azurerm_storage_account` | `{prefix}metastore{random}` | Metastore root storage | Resource Group |
| `azurerm_storage_container` | `metastore` | Metastore data container | Storage Account |
| `azurerm_storage_account` | `{prefix}external{random}` | External location storage | Resource Group |
| `azurerm_storage_container` | `external` | External data container | Storage Account |
| `azurerm_databricks_access_connector` | `{prefix}-access-connector` | Managed identity | Resource Group |
| `azurerm_role_assignment` | (auto) | Storage Blob Data Contributor | Storage Accounts |
| `databricks_metastore_data_access` | `{prefix}-metastore-access` | Metastore storage credential | Metastore |
| `databricks_metastore_assignment` | (auto) | Workspace → Metastore link | Workspace |
| `databricks_storage_credential` | `{prefix}-external-credential` | External storage credential | Workspace |
| `databricks_external_location` | `{prefix}-external-location` | External location | Workspace |

---

## Variables

### Metastore Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `create_metastore` | bool | `true` | Create new metastore (true) or use existing (false) |
| `existing_metastore_id` | string | `""` | Existing metastore ID (required if `create_metastore=false`) |
| `metastore_name` | string | `""` | Metastore name (auto-generated if empty) |
| `databricks_account_id` | string | (required) | Databricks account ID (UUID format) |

**Metastore Strategies**:

| Scenario | `create_metastore` | `existing_metastore_id` | Behavior |
|----------|-------------------|------------------------|----------|
| **First workspace in region** | `true` | `""` | Creates new metastore |
| **Additional workspace in region** | `false` | `"abc-123..."` | Uses existing metastore |

### Workspace Configuration

| Variable | Type | Description |
|----------|------|-------------|
| `workspace_id` | string | Workspace ID (numeric) for metastore assignment |
| `workspace_prefix` | string | Naming prefix for resources |

### Storage Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `location` | string | (required) | Azure region |
| `resource_group_name` | string | (required) | Resource group for UC resources |
| `create_metastore_storage` | bool | `true` | Create metastore storage account |
| `create_external_location_storage` | bool | `true` | Create external location storage |

**Storage Naming**:
- Metastore: `{prefix}metastore{random}` (e.g., `proddbmetastore9a8b`)
- External: `{prefix}external{random}` (e.g., `proddbexternal9a8b`)

### Access Connector Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `create_access_connector` | bool | `true` | Create new Access Connector |
| `existing_access_connector_id` | string | `""` | Existing Access Connector ID |
| `existing_access_connector_principal_id` | string | `""` | Existing Access Connector principal ID |

**Access Connector Strategies**:

| Strategy | `create_access_connector` | `existing_*` | Use Case |
|----------|--------------------------|--------------|----------|
| **Per-Workspace** | `true` | `""` | Default, workspace isolation |
| **Shared (Regional)** | `false` | Provide IDs | Shared governance across workspaces |

### Storage Connectivity

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `enable_private_link_storage` | bool | `false` | Use Private Link for storage (vs. Service Endpoints) |
| `storage_private_endpoint_subnet_id` | string | `""` | Subnet ID for private endpoints |
| `service_endpoints_enabled` | bool | `true` | Service endpoints enabled on subnets |

**Connectivity Options**:

| Pattern | `enable_private_link_storage` | `service_endpoints_enabled` | Performance |
|---------|-------------------------------|----------------------------|-------------|
| **Service Endpoints** (default) | `false` | `true` | Excellent |
| **Private Link** (optional) | `true` | Any | Excellent |

---

## Outputs

| Output | Description |
|--------|-------------|
| `metastore_id` | Unity Catalog metastore ID |
| `metastore_name` | Metastore name |
| `workspace_metastore_id` | Workspace metastore assignment ID |
| `metastore_storage_account_name` | Metastore storage account name |
| `external_storage_account_name` | External location storage account name |
| `storage_account_fqdns` | List of all storage account FQDNs (for SEP) |
| `access_connector_id` | Access Connector resource ID |
| `external_location_url` | External location URL |
| `storage_credential_name` | Storage credential name |

---

## Metastore Lifecycle

### force_destroy = true

**CRITICAL**: This module sets `force_destroy = true` on all metastore resources:

```hcl
resource "databricks_metastore" "this" {
  force_destroy = true  # Allows clean destroy with root credential
}
```

**Why This Matters**:
- ✅ Allows `terraform destroy` to delete metastore even with root credential attached
- ✅ Prevents "cannot delete metastore data access" errors
- ✅ Does NOT make deletion dangerous - requires explicit `terraform destroy`
- ✅ Production-safe - metastore deletion still requires user confirmation

**DO NOT**:
- ❌ Set `force_destroy = false`
- ❌ Add `lifecycle.ignore_changes = [force_destroy]`
- ❌ Remove `force_destroy` attribute

See [Troubleshooting Guide](../TROUBLESHOOTING.md#unity-catalog-destroy-issues) for details.

---

## Storage Accounts

### Network Configuration

**Default (Service Endpoints)**:
```hcl
network_rules {
  default_action = "Allow"  # Required for initial creation
  bypass         = ["AzureServices"]
  # Can be locked down post-deployment
}
```

**Why `default_action = "Allow"`**:
- Allows Terraform (running locally) to create containers
- Prevents 403 authorization errors during deployment
- Can be manually locked down after deployment
- Service Endpoints provide security via backbone routing

**Optional Private Link**:
```hcl
resource "azurerm_private_endpoint" "metastore_storage" {
  count = var.enable_private_link_storage ? 1 : 0
  # Creates private endpoint for storage account
}
```

### Storage Features

- ✅ **ADLS Gen2**: Hierarchical Namespace enabled
- ✅ **Replication**: LRS (locally redundant storage)
- ✅ **Tier**: Standard (hot tier)
- ✅ **Secure Transfer**: HTTPS required
- ✅ **TLS Version**: 1.2 minimum
- ✅ **Service Endpoints**: Always enabled
- ✅ **Tags**: Applied to all resources

---

## RBAC Configuration

### Storage Account Permissions

```hcl
resource "azurerm_role_assignment" "metastore_contributor" {
  scope                = azurerm_storage_account.metastore[0].id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = local.access_connector_principal_id
}
```

**Permissions Granted**:
- Read, write, delete blobs
- List containers
- Manage blob properties
- Manage blob metadata

**Applied To**:
- Metastore root storage account
- External location storage account

---

## Usage Examples

### Example 1: First Workspace in Region (Create Metastore)

```hcl
module "unity_catalog" {
  source = "../../modules/unity-catalog"
  
  # Metastore configuration (create new)
  create_metastore      = true
  metastore_name        = "prod-eastus2-metastore"
  databricks_account_id = var.databricks_account_id
  
  # Workspace configuration
  workspace_id     = module.workspace.workspace_id_numeric
  workspace_prefix = "proddb"
  
  # Storage configuration
  location            = "eastus2"
  resource_group_name = azurerm_resource_group.this.name
  
  # Access Connector (create new)
  create_access_connector = true
  
  # Storage connectivity (Service Endpoints - default)
  enable_private_link_storage = false
  service_endpoints_enabled   = true
  
  # Databricks providers
  providers = {
    databricks.account   = databricks.account
    databricks.workspace = databricks.workspace
  }
  
  tags = {
    Environment = "Production"
  }
}
```

### Example 2: Additional Workspace (Use Existing Metastore)

```hcl
module "unity_catalog" {
  source = "../../modules/unity-catalog"
  
  # Metastore configuration (use existing)
  create_metastore       = false
  existing_metastore_id  = "abc-123-def-456"  # From first workspace
  databricks_account_id  = var.databricks_account_id
  
  # Workspace configuration
  workspace_id     = module.workspace.workspace_id_numeric
  workspace_prefix = "devdb"
  
  # Storage configuration
  location                        = "eastus2"
  resource_group_name             = azurerm_resource_group.this.name
  create_metastore_storage        = false  # Skip metastore storage
  create_external_location_storage = true   # Create workspace storage
  
  # Access Connector (create new per workspace)
  create_access_connector = true
  
  # Storage connectivity
  enable_private_link_storage = false
  service_endpoints_enabled   = true
  
  providers = {
    databricks.account   = databricks.account
    databricks.workspace = databricks.workspace
  }
  
  tags = {
    Environment = "Development"
  }
}
```

### Example 3: Private Link Storage

```hcl
module "unity_catalog" {
  source = "../../modules/unity-catalog"
  
  create_metastore      = true
  metastore_name        = "private-eastus2-metastore"
  databricks_account_id = var.databricks_account_id
  
  workspace_id     = module.workspace.workspace_id_numeric
  workspace_prefix = "privatedb"
  
  location            = "eastus2"
  resource_group_name = azurerm_resource_group.this.name
  
  create_access_connector = true
  
  # Private Link enabled
  enable_private_link_storage         = true
  storage_private_endpoint_subnet_id  = module.networking.private_subnet_id
  
  providers = {
    databricks.account   = databricks.account
    databricks.workspace = databricks.workspace
  }
  
  tags = {
    Environment = "Production"
    Connectivity = "PrivateLink"
  }
}
```

### Example 4: Shared Access Connector (Regional)

```hcl
# First workspace: Create Access Connector
module "unity_catalog_ws1" {
  source = "../../modules/unity-catalog"
  
  # ... other config ...
  
  create_access_connector = true
}

# Capture Access Connector details
output "shared_access_connector_id" {
  value = module.unity_catalog_ws1.access_connector_id
}

output "shared_access_connector_principal_id" {
  value = module.unity_catalog_ws1.access_connector_principal_id
}

# Second workspace: Use existing Access Connector
module "unity_catalog_ws2" {
  source = "../../modules/unity-catalog"
  
  # ... other config ...
  
  # Use shared Access Connector
  create_access_connector                = false
  existing_access_connector_id           = module.unity_catalog_ws1.access_connector_id
  existing_access_connector_principal_id = module.unity_catalog_ws1.access_connector_principal_id
}
```

---

## Best Practices

### Metastore Strategy

1. **One Metastore Per Region**
   - First workspace: Create metastore
   - Additional workspaces: Use existing metastore
   - Document metastore ID for reuse

2. **Naming Convention**
   ```hcl
   metastore_name = "${var.environment}-${var.location}-metastore"
   # Examples:
   # - prod-eastus2-metastore
   # - staging-westus2-metastore
   ```

3. **Metastore Governance**
   - Assign metastore admins
   - Configure catalog permissions
   - Enable audit logging

### Storage Strategy

1. **Separation of Concerns**
   - Metastore storage: Shared metadata
   - External location: Per-workspace data
   - Clear separation for security and billing

2. **Storage Connectivity**
   - Default: Service Endpoints
   - Compliance: Private Link
   - Test connectivity before production

3. **Storage Lifecycle**
   - Enable soft delete (7+ days)
   - Configure retention policies
   - Plan for data archival

### Access Connector Strategy

| Approach | When to Use | Benefits | Drawbacks |
|----------|------------|----------|-----------|
| **Per-Workspace** | Default | Isolation, clear RBAC | More resources |
| **Shared (Regional)** | Multi-workspace | Fewer resources, centralized | Shared permissions |

---

## Troubleshooting

### Issue: Metastore Already Exists

**Error**:
```
Error: cannot create metastore: Metastore 'prod-eastus2-metastore' already exists
```

**Solution**: Use existing metastore:
```hcl
create_metastore      = false
existing_metastore_id = "abc-123-def-456"
```

### Issue: 403 Authorization Error (Storage)

**Error**:
```
Error: checking for existing Container "metastore": unexpected status 403
```

**Solution**: Storage account network rules are too restrictive. Module uses `default_action = "Allow"` during creation.

### Issue: Cannot Delete Metastore

**Error**:
```
Error: cannot delete metastore data access: Storage credential cannot be deleted
```

**Solution**: Module already sets `force_destroy = true`. If error persists, remove from state:
```bash
terraform state rm 'module.unity_catalog.databricks_metastore.this[0]'
```

See [Troubleshooting Guide](../TROUBLESHOOTING.md) for more details.

---

## References

- [Unity Catalog Overview](https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/)
- [Unity Catalog Best Practices](https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/best-practices)
- [Storage Credentials](https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/manage-external-locations-and-credentials)
- [Access Connectors](https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/azure-managed-identities)
- [Service Endpoints](https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/service-endpoints)

---

**Module Version**: 1.0  
**Terraform Version**: >= 1.5
