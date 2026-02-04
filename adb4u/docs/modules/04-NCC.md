# Network Connectivity Configuration (NCC) Module

**Module Path**: `modules/ncc`  
**Status**: ✅ **Production Ready**  
**Mandatory**: Yes (like Unity Catalog)

---

## Overview

The Network Connectivity Configuration (NCC) module creates and manages the **Network Connectivity Configuration** for Azure Databricks serverless compute.

### What is NCC?

NCC enables **serverless compute** (SQL Warehouses, Serverless Notebooks) to securely connect to customer Azure resources:
- Unity Catalog storage accounts
- External customer storage (ADLS Gen2)
- Other Azure services (Key Vault, Event Hub, etc.)

### Why is NCC Mandatory?

Just like Unity Catalog, NCC is a **required component** for modern Databricks workspaces:
- ✅ Enables serverless compute capabilities
- ✅ Provides secure connectivity without VNet injection
- ✅ Supports both Service Endpoints and Private Link
- ✅ Future-proofs the workspace for serverless adoption

---

## Architecture

### How NCC Works

```
┌─────────────────────────────────────────────────────────────┐
│ Databricks Serverless Compute Plane                         │
│ (Microsoft-Managed VNet)                                     │
│                                                              │
│  ┌──────────────────┐        ┌──────────────────┐          │
│  │ SQL Warehouses   │        │ Serverless       │          │
│  │                  │        │ Notebooks        │          │
│  └──────────────────┘        └──────────────────┘          │
└─────────────────────────────────────────────────────────────┘
                │                         │
                └────────────┬────────────┘
                             │
                ┌────────────▼───────────┐
                │ Network Connectivity   │
                │ Configuration (NCC)    │
                │ - Config + Binding     │
                │ - PE Rules (optional)  │
                └────────────┬───────────┘
                             │
          ┌──────────────────┴──────────────────┐
          │                                      │
    ┌─────▼─────┐                         ┌─────▼─────┐
    │ Service   │                         │ Private   │
    │ Endpoints │                         │ Link      │
    └─────┬─────┘                         └─────┬─────┘
          │                                      │
          └──────────────────┬───────────────────┘
                             │
          ┌──────────────────▼──────────────────┐
          │ Customer Azure Resources            │
          │ - Storage Accounts                  │
          │ - Key Vaults                        │
          │ - Other Services                    │
          └─────────────────────────────────────┘
```

---

## Module Components

### Resources Created

The NCC module creates **2 resources**:

1. **`databricks_mws_network_connectivity_config`**
   - NCC configuration at account level
   - Can be shared across multiple workspaces
   - Reusable and referenceable

2. **`databricks_mws_ncc_binding`**
   - Binds NCC to specific workspace
   - One binding per workspace

### Resources NOT Created

The module **does NOT create**:
- ❌ `databricks_mws_ncc_private_endpoint_rule` - Private Endpoint rules

**Why?**: PE rules require manual approval in Azure Portal (cross-account connections). They are created:
- **Manually** by customer in Databricks UI
- **After** workspace deployment
- **Only if** using Private Link option

---

## Usage

### Basic Usage (All Deployments)

```hcl
module "ncc" {
  source = "../../modules/ncc"

  providers = {
    databricks.account = databricks.account
  }

  # Required
  workspace_id_numeric = module.workspace.workspace_id_numeric
  workspace_prefix     = var.workspace_prefix
  location             = var.location

  depends_on = [module.unity_catalog]
}
```

### Outputs

```hcl
output "ncc_id" {
  description = "Network Connectivity Configuration ID"
  value       = module.ncc.ncc_id
}

output "ncc_name" {
  description = "Network Connectivity Configuration name"
  value       = module.ncc.ncc_name
}
```

---

## Variables

### Required Variables

| Variable | Type | Description |
|----------|------|-------------|
| `workspace_id_numeric` | `string` | Numeric Databricks workspace ID (not Azure resource ID) |
| `workspace_prefix` | `string` | Prefix for resource naming (lowercase alphanumeric, max 12 chars) |
| `location` | `string` | Azure region for NCC configuration |

### Optional Variables

None. The module has minimal configuration by design.

---

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| `ncc_id` | `string` | Network Connectivity Configuration ID (format: `ncc-<id>`) |
| `ncc_name` | `string` | Network Connectivity Configuration name |

---

## Post-Deployment Setup

### Classic Clusters

✅ **No setup required** - Classic clusters work immediately using VNet connectivity.

### Serverless Compute

⏸️ **Manual setup required** - Choose one of two options:

#### **Option A: Service Endpoints** (Recommended for Non-PL)

**When to Use**:
- Non-Private Link deployments
- Cost-sensitive scenarios
- Simpler setup preferred

**Setup Steps**:
1. Enable serverless in Databricks UI
2. Get serverless subnet IDs
3. Add subnets to storage firewall

**Documentation**:
- [Non-PL Serverless Setup](../../deployments/non-pl/docs/SERVERLESS-SETUP.md)

---

#### **Option B: Private Link** (Mandatory for Full-Private)

**When to Use**:
- Full Private deployments (mandatory)
- Highly regulated environments
- Zero-trust network requirements

**Setup Steps**:
1. Enable serverless with Private Link in Databricks UI
2. Databricks creates PE connections (shows "Pending")
3. Approve connections in Azure Portal
4. Verify status shows "Connected"

**Documentation**:
- [Full-Private Serverless Setup](../../deployments/full-private/docs/04-SERVERLESS-SETUP.md)

---

## Deployment Patterns

### Non-PL Pattern

```hcl
# NCC created automatically (mandatory)
module "ncc" {
  source = "../../modules/ncc"
  
  providers = {
    databricks.account = databricks.account
  }
  
  workspace_id_numeric = module.workspace.workspace_id_numeric
  workspace_prefix     = var.workspace_prefix
  location             = var.location
  
  depends_on = [module.unity_catalog]
}
```

**Serverless Options**: Service Endpoints OR Private Link

---

### Full-Private Pattern

```hcl
# NCC created automatically (mandatory)
module "ncc" {
  source = "../../modules/ncc"
  
  providers = {
    databricks.account = databricks.account
  }
  
  workspace_id_numeric = module.workspace.workspace_id_numeric
  workspace_prefix     = var.workspace_prefix
  location             = var.location
  
  depends_on = [module.unity_catalog]
}
```

**Serverless Options**: Private Link ONLY (consistent with air-gapped design)

---

## Troubleshooting

### Issue: NCC Not Found in Outputs

**Symptoms**:
```bash
terraform output ncc_id
# Error: Output not found
```

**Cause**: Module not included in deployment (legacy configuration)

**Solution**: Add NCC module to `main.tf` (see [Usage](#usage))

---

### Issue: Cannot Create NCC

**Error**:
```
Error: cannot create network connectivity config: Unauthorized
```

**Cause**: Databricks account provider not configured correctly

**Solution**:
```hcl
# Ensure account provider is configured
terraform {
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      configuration_aliases = [databricks.account]
    }
  }
}

# In providers.tf
provider "databricks" {
  alias      = "account"
  host       = "https://accounts.azuredatabricks.net"
  account_id = var.databricks_account_id
}
```

---

### Issue: NCC Binding Fails

**Error**:
```
Error: cannot bind ncc to workspace: Workspace not found
```

**Cause**: Workspace not fully created yet

**Solution**: Ensure `depends_on` includes workspace and Unity Catalog:
```hcl
module "ncc" {
  # ...
  depends_on = [module.unity_catalog]  # UC depends on workspace
}
```

---

### Issue: Cannot Delete NCC (Attached to Workspace)

**Error**:
```
Error: Network Connectivity Config is unable to be deleted because 
it is attached to one or more workspaces
```

**Cause**: NCC binding must be deleted before NCC config

**Solution**: Remove from Terraform state
```bash
terraform state rm 'module.ncc.databricks_mws_ncc_binding.this'
terraform state rm 'module.ncc.databricks_mws_network_connectivity_config.this'
terraform destroy
```

**Why**: NCC is account-level and can be reused across workspaces.

---

## Best Practices

### 1. Always Include NCC

✅ **DO**: Include NCC in all deployments
```hcl
module "ncc" {
  source = "../../modules/ncc"
  # ...
}
```

❌ **DON'T**: Make NCC optional or conditional

**Reason**: NCC is mandatory for serverless, which is increasingly the default compute mode.

---

### 2. Depend on Unity Catalog

✅ **DO**: Add dependency on Unity Catalog
```hcl
module "ncc" {
  # ...
  depends_on = [module.unity_catalog]
}
```

❌ **DON'T**: Create NCC before workspace is fully initialized

**Reason**: NCC binding requires a fully created workspace with UC.

---

### 3. Don't Create PE Rules in Terraform

✅ **DO**: Leave PE rules for manual setup
```hcl
# NCC module creates config + binding only
# NO databricks_mws_ncc_private_endpoint_rule resources
```

❌ **DON'T**: Try to automate PE rule creation

**Reason**: Requires manual approval in Azure Portal (cross-account).

---

### 4. Document Serverless Setup

✅ **DO**: Provide clear serverless setup documentation
```markdown
Post-deployment: See docs/SERVERLESS-SETUP.md for enabling serverless compute
```

❌ **DON'T**: Assume users know how to enable serverless

**Reason**: Serverless requires additional steps not automated by Terraform.

---

## Examples

### Example: Non-PL Deployment

```hcl
# main.tf
module "workspace" {
  source = "../../modules/workspace"
  # ... workspace config
}

module "unity_catalog" {
  source = "../../modules/unity-catalog"
  # ... UC config
  depends_on = [module.workspace]
}

module "ncc" {
  source = "../../modules/ncc"
  
  providers = {
    databricks.account = databricks.account
  }
  
  workspace_id_numeric = module.workspace.workspace_id_numeric
  workspace_prefix     = var.workspace_prefix
  location             = var.location
  
  depends_on = [module.unity_catalog]
}

# Outputs
output "ncc_status" {
  value = {
    ncc_id   = module.ncc.ncc_id
    ncc_name = module.ncc.ncc_name
    message  = "Serverless-ready. See docs/SERVERLESS-SETUP.md for configuration."
  }
}
```

---

### Example: Full-Private Deployment

```hcl
# main.tf
module "workspace" {
  source = "../../modules/workspace"
  # ... workspace config with Private Link
  enable_private_link = true
}

module "unity_catalog" {
  source = "../../modules/unity-catalog"
  # ... UC config with Private Endpoints
  enable_private_link_storage = true
  depends_on = [module.workspace]
}

module "ncc" {
  source = "../../modules/ncc"
  
  providers = {
    databricks.account = databricks.account
  }
  
  workspace_id_numeric = module.workspace.workspace_id_numeric
  workspace_prefix     = var.workspace_prefix
  location             = var.location
  
  depends_on = [module.unity_catalog]
}

# Outputs
output "serverless_setup_required" {
  value = "Private Link approval required for serverless. See docs/04-SERVERLESS-SETUP.md"
}
```

---

## References

**Azure Databricks Documentation**:
- [Serverless Network Security](https://learn.microsoft.com/en-us/azure/databricks/security/network/serverless-network-security/)
- [Network Connectivity Configuration](https://learn.microsoft.com/en-us/azure/databricks/security/network/serverless-network-security/serverless-private-link)

**Related Modules**:
- [Workspace Module](./WORKSPACE.md)
- [Unity Catalog Module](./UNITY-CATALOG.md)
- [Networking Module](./NETWORKING.md)

**Deployment Guides**:
- [Non-PL Serverless Setup](../../deployments/non-pl/docs/SERVERLESS-SETUP.md)
- [Full-Private Serverless Setup](../../deployments/full-private/docs/04-SERVERLESS-SETUP.md)

---

**Module**: NCC (Network Connectivity Configuration)  
**Status**: ✅ Production Ready
