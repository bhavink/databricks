***REMOVED*** Network Connectivity Configuration (NCC) Module

**Module Path**: `modules/ncc`  
**Status**: ✅ **Production Ready**  
**Mandatory**: Yes (like Unity Catalog)

---

***REMOVED******REMOVED*** Overview

The Network Connectivity Configuration (NCC) module creates and manages the **Network Connectivity Configuration** for Azure Databricks serverless compute.

***REMOVED******REMOVED******REMOVED*** What is NCC?

NCC enables **serverless compute** (SQL Warehouses, Serverless Notebooks) to securely connect to customer Azure resources:
- Unity Catalog storage accounts
- External customer storage (ADLS Gen2)
- Other Azure services (Key Vault, Event Hub, etc.)

***REMOVED******REMOVED******REMOVED*** Why is NCC Mandatory?

Just like Unity Catalog, NCC is a **required component** for modern Databricks workspaces:
- ✅ Enables serverless compute capabilities
- ✅ Provides secure connectivity without VNet injection
- ✅ Supports both Service Endpoints and Private Link
- ✅ Future-proofs the workspace for serverless adoption

---

***REMOVED******REMOVED*** Architecture

***REMOVED******REMOVED******REMOVED*** How NCC Works

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

***REMOVED******REMOVED*** Module Components

***REMOVED******REMOVED******REMOVED*** Resources Created

The NCC module creates **2 resources**:

1. **`databricks_mws_network_connectivity_config`**
   - NCC configuration at account level
   - Can be shared across multiple workspaces
   - Reusable and referenceable

2. **`databricks_mws_ncc_binding`**
   - Binds NCC to specific workspace
   - One binding per workspace

***REMOVED******REMOVED******REMOVED*** Resources NOT Created

The module **does NOT create**:
- ❌ `databricks_mws_ncc_private_endpoint_rule` - Private Endpoint rules

**Why?**: PE rules require manual approval in Azure Portal (cross-account connections). They are created:
- **Manually** by customer in Databricks UI
- **After** workspace deployment
- **Only if** using Private Link option

---

***REMOVED******REMOVED*** Usage

***REMOVED******REMOVED******REMOVED*** Basic Usage (All Deployments)

```hcl
module "ncc" {
  source = "../../modules/ncc"

  providers = {
    databricks.account = databricks.account
  }

  ***REMOVED*** Required
  workspace_id_numeric = module.workspace.workspace_id_numeric
  workspace_prefix     = var.workspace_prefix
  location             = var.location

  depends_on = [module.unity_catalog]
}
```

***REMOVED******REMOVED******REMOVED*** Outputs

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

***REMOVED******REMOVED*** Variables

***REMOVED******REMOVED******REMOVED*** Required Variables

| Variable | Type | Description |
|----------|------|-------------|
| `workspace_id_numeric` | `string` | Numeric Databricks workspace ID (not Azure resource ID) |
| `workspace_prefix` | `string` | Prefix for resource naming (lowercase alphanumeric, max 12 chars) |
| `location` | `string` | Azure region for NCC configuration |

***REMOVED******REMOVED******REMOVED*** Optional Variables

None. The module has minimal configuration by design.

---

***REMOVED******REMOVED*** Outputs

| Output | Type | Description |
|--------|------|-------------|
| `ncc_id` | `string` | Network Connectivity Configuration ID (format: `ncc-<id>`) |
| `ncc_name` | `string` | Network Connectivity Configuration name |

---

***REMOVED******REMOVED*** Post-Deployment Setup

***REMOVED******REMOVED******REMOVED*** Classic Clusters

✅ **No setup required** - Classic clusters work immediately using VNet connectivity.

***REMOVED******REMOVED******REMOVED*** Serverless Compute

⏸️ **Manual setup required** - Choose one of two options:

***REMOVED******REMOVED******REMOVED******REMOVED*** **Option A: Service Endpoints** (Recommended for Non-PL)

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

***REMOVED******REMOVED******REMOVED******REMOVED*** **Option B: Private Link** (Mandatory for Full-Private)

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

***REMOVED******REMOVED*** Deployment Patterns

***REMOVED******REMOVED******REMOVED*** Non-PL Pattern

```hcl
***REMOVED*** NCC created automatically (mandatory)
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

***REMOVED******REMOVED******REMOVED*** Full-Private Pattern

```hcl
***REMOVED*** NCC created automatically (mandatory)
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

***REMOVED******REMOVED*** Troubleshooting

***REMOVED******REMOVED******REMOVED*** Issue: NCC Not Found in Outputs

**Symptoms**:
```bash
terraform output ncc_id
***REMOVED*** Error: Output not found
```

**Cause**: Module not included in deployment (legacy configuration)

**Solution**: Add NCC module to `main.tf` (see [Usage](***REMOVED***usage))

---

***REMOVED******REMOVED******REMOVED*** Issue: Cannot Create NCC

**Error**:
```
Error: cannot create network connectivity config: Unauthorized
```

**Cause**: Databricks account provider not configured correctly

**Solution**:
```hcl
***REMOVED*** Ensure account provider is configured
terraform {
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      configuration_aliases = [databricks.account]
    }
  }
}

***REMOVED*** In providers.tf
provider "databricks" {
  alias      = "account"
  host       = "https://accounts.azuredatabricks.net"
  account_id = var.databricks_account_id
}
```

---

***REMOVED******REMOVED******REMOVED*** Issue: NCC Binding Fails

**Error**:
```
Error: cannot bind ncc to workspace: Workspace not found
```

**Cause**: Workspace not fully created yet

**Solution**: Ensure `depends_on` includes workspace and Unity Catalog:
```hcl
module "ncc" {
  ***REMOVED*** ...
  depends_on = [module.unity_catalog]  ***REMOVED*** UC depends on workspace
}
```

---

***REMOVED******REMOVED******REMOVED*** Issue: Cannot Delete NCC (Attached to Workspace)

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

***REMOVED******REMOVED*** Best Practices

***REMOVED******REMOVED******REMOVED*** 1. Always Include NCC

✅ **DO**: Include NCC in all deployments
```hcl
module "ncc" {
  source = "../../modules/ncc"
  ***REMOVED*** ...
}
```

❌ **DON'T**: Make NCC optional or conditional

**Reason**: NCC is mandatory for serverless, which is increasingly the default compute mode.

---

***REMOVED******REMOVED******REMOVED*** 2. Depend on Unity Catalog

✅ **DO**: Add dependency on Unity Catalog
```hcl
module "ncc" {
  ***REMOVED*** ...
  depends_on = [module.unity_catalog]
}
```

❌ **DON'T**: Create NCC before workspace is fully initialized

**Reason**: NCC binding requires a fully created workspace with UC.

---

***REMOVED******REMOVED******REMOVED*** 3. Don't Create PE Rules in Terraform

✅ **DO**: Leave PE rules for manual setup
```hcl
***REMOVED*** NCC module creates config + binding only
***REMOVED*** NO databricks_mws_ncc_private_endpoint_rule resources
```

❌ **DON'T**: Try to automate PE rule creation

**Reason**: Requires manual approval in Azure Portal (cross-account).

---

***REMOVED******REMOVED******REMOVED*** 4. Document Serverless Setup

✅ **DO**: Provide clear serverless setup documentation
```markdown
Post-deployment: See docs/SERVERLESS-SETUP.md for enabling serverless compute
```

❌ **DON'T**: Assume users know how to enable serverless

**Reason**: Serverless requires additional steps not automated by Terraform.

---

***REMOVED******REMOVED*** Examples

***REMOVED******REMOVED******REMOVED*** Example: Non-PL Deployment

```hcl
***REMOVED*** main.tf
module "workspace" {
  source = "../../modules/workspace"
  ***REMOVED*** ... workspace config
}

module "unity_catalog" {
  source = "../../modules/unity-catalog"
  ***REMOVED*** ... UC config
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

***REMOVED*** Outputs
output "ncc_status" {
  value = {
    ncc_id   = module.ncc.ncc_id
    ncc_name = module.ncc.ncc_name
    message  = "Serverless-ready. See docs/SERVERLESS-SETUP.md for configuration."
  }
}
```

---

***REMOVED******REMOVED******REMOVED*** Example: Full-Private Deployment

```hcl
***REMOVED*** main.tf
module "workspace" {
  source = "../../modules/workspace"
  ***REMOVED*** ... workspace config with Private Link
  enable_private_link = true
}

module "unity_catalog" {
  source = "../../modules/unity-catalog"
  ***REMOVED*** ... UC config with Private Endpoints
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

***REMOVED*** Outputs
output "serverless_setup_required" {
  value = "Private Link approval required for serverless. See docs/04-SERVERLESS-SETUP.md"
}
```

---

***REMOVED******REMOVED*** References

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
