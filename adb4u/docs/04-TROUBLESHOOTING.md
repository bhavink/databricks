***REMOVED*** Troubleshooting Guide

This document contains solutions to common issues encountered during deployment, updates, and destruction of Azure Databricks workspaces.

---

***REMOVED******REMOVED*** Table of Contents

1. [Destroy & Cleanup Issues](***REMOVED***destroy--cleanup-issues)
2. [Unity Catalog Issues](***REMOVED***unity-catalog-issues)
3. [Network Configuration Issues](***REMOVED***network-configuration-issues)
4. [Authentication Issues](***REMOVED***authentication-issues)
5. [Storage Account Access](***REMOVED***storage-account-access)
6. [Quick Reference Commands](***REMOVED***quick-reference-commands)
7. [Debugging Tips](***REMOVED***debugging-tips)

---

***REMOVED******REMOVED*** Destroy & Cleanup Issues

***REMOVED******REMOVED******REMOVED*** Issue: Service Endpoint Policy Cannot Be Deleted

**Error Message**:
```
Error: ServiceEndpointPolicyCannotBeDeletedIfReferencedBySubnet
Service Endpoint Policy cannot be deleted because it is in use with subnet(s).
```

**Root Cause**:
Azure prevents deletion of a Service Endpoint Policy while it's still referenced by subnets.

**Solutions**:

**For New Deployments** (created after graceful destroy fix):
```bash
terraform destroy  ***REMOVED*** Automatic cleanup
```

**For Existing Deployments** (created before graceful destroy fix):
```bash
***REMOVED*** Step 1: Remove SEP from subnets manually
az network vnet subnet update \
  --resource-group <RG_NAME> \
  --vnet-name <VNET_NAME> \
  --name <PUBLIC_SUBNET_NAME> \
  --remove serviceEndpointPolicies

az network vnet subnet update \
  --resource-group <RG_NAME> \
  --vnet-name <VNET_NAME> \
  --name <PRIVATE_SUBNET_NAME> \
  --remove serviceEndpointPolicies

***REMOVED*** Step 2: Destroy
terraform destroy
```

**How to find your resource names:**
```bash
terraform output -raw resources | jq -r '.network.vnet_name'
terraform output -raw resources | jq -r '.network.subnet_names'
```

---

***REMOVED******REMOVED******REMOVED*** Issue: Network Connectivity Config Cannot Be Deleted

**Error Message**:
```
Error: Network Connectivity Config is unable to be deleted because 
it is attached to one or more workspaces
```

**Root Cause**:
NCC binding removal has propagation delay; API still sees it as "attached" when deletion is attempted.

**Solution**:
```bash
***REMOVED*** Remove NCC from state (workspace deletion will clean it up)
terraform state rm module.ncc.databricks_mws_network_connectivity_config.this

***REMOVED*** Continue with destroy
terraform destroy
```

**Why this is safe:**
- NCC is workspace-specific
- When workspace is deleted, NCC binding is automatically removed
- This is a known Databricks API timing limitation

---

***REMOVED******REMOVED*** Unity Catalog Issues

***REMOVED******REMOVED******REMOVED*** Issue: Cannot Delete Metastore Data Access

**Error Message**:
```
Error: cannot delete metastore data access: Storage credential 'xxx-metastore-access' 
cannot be deleted because it is configured as this metastore's root credential.
```

**Root Cause**:
Unity Catalog protects the root storage credential from deletion to prevent data access issues. The `force_destroy` parameter may not work in all cases due to API limitations.

**Solution**:
```bash
***REMOVED*** Remove metastore resources from state
terraform state rm module.unity_catalog.databricks_metastore_data_access.this
terraform state rm module.unity_catalog.databricks_metastore.this

***REMOVED*** Continue with destroy
terraform destroy
```

**Prevention** (for new deployments):
```hcl
***REMOVED*** modules/unity-catalog/main.tf
resource "databricks_metastore" "this" {
  provider      = databricks.account
  name          = var.metastore_name
  storage_root  = "abfss://..."
  region        = var.location
  force_destroy = true  ***REMOVED*** Set on initial creation
}
```

**Important Notes**:
- ✅ **DO** set `force_destroy = true` in production deployments
- ⚠️ Metastore can be manually cleaned up later from Databricks Account Console if needed
- 🔒 Setting `force_destroy = true` doesn't make deletion dangerous - it only allows Terraform to delete when you explicitly run `terraform destroy`

---

***REMOVED******REMOVED******REMOVED*** Issue: Metastore Update Validation Error

**Error Message**:
```
Error: cannot update metastore: UpdateMetastore delta_sharing_recipient_token_lifetime_in_seconds 
can not be 0, which is infinite token lifetime.
```

**Root Cause**:
The Databricks API validates certain metastore parameters during updates. Setting `force_destroy` from `false` to `true` triggers an update operation that fails API validation.

**Solution**:
Remove metastore from state and continue:
```bash
terraform state rm module.unity_catalog.databricks_metastore_data_access.this
terraform state rm module.unity_catalog.databricks_metastore.this
terraform destroy
```

---

***REMOVED******REMOVED*** Network Configuration Issues

***REMOVED******REMOVED******REMOVED*** Issue: NSG Rule Conflicts with Databricks

**Error Message**:
```
Error: Security rule AllowVnetInBound conflicts with rule 
Microsoft.Databricks-workspaces_UseOnly_databricks-worker-to-worker-inbound.
```

**Root Cause**:
In Non-PL deployments, Databricks automatically creates NSG rules. Custom rules conflict with these.

**Solution**:
NSG rule creation is already conditional - only for Private Link deployments:

```hcl
***REMOVED*** modules/networking/nsg-rules.tf
resource "azurerm_network_security_rule" "inbound_vnet_to_vnet" {
  count = var.enable_private_link && !var.enable_public_network_access ? 1 : 0
  ***REMOVED*** ...
}
```

**Rule Summary**:
- **Non-PL**: Databricks manages NSG rules automatically ✅
- **Private Link**: Custom NSG rules are created ✅

---

***REMOVED******REMOVED*** Authentication Issues

***REMOVED******REMOVED******REMOVED*** Issue: Failed to Retrieve Tenant ID

**Error Message**:
```
Error: cannot create metastore: Failed to retrieve tenant ID for given token
```

**Root Cause**:
Missing `DATABRICKS_AZURE_TENANT_ID` environment variable for Databricks account provider.

**Solution**:
Export required environment variables:

```bash
***REMOVED*** Azure Authentication
export ARM_SUBSCRIPTION_ID="your-subscription-id"
export ARM_TENANT_ID="your-tenant-id"
export ARM_CLIENT_ID="your-client-id"          ***REMOVED*** If using service principal
export ARM_CLIENT_SECRET="your-client-secret"  ***REMOVED*** If using service principal

***REMOVED*** Databricks Authentication
export DATABRICKS_ACCOUNT_ID="your-account-id"
export DATABRICKS_AZURE_TENANT_ID="$ARM_TENANT_ID"
```

**Provider Configuration**:
```hcl
***REMOVED*** deployments/*/providers.tf
provider "databricks" {
  alias             = "account"
  host              = "https://accounts.azuredatabricks.net"
  account_id        = var.databricks_account_id
  azure_tenant_id   = var.databricks_azure_tenant_id
  azure_use_msi     = false
  azure_environment = "public"
}
```

---

***REMOVED******REMOVED*** Storage Account Access

***REMOVED******REMOVED******REMOVED*** Issue: 403 Authorization Error During Container Creation

**Error Message**:
```
Error: checking for existing Container "metastore": unexpected status 403 
(403 This request is not authorized to perform this operation.)
```

**Root Cause**:
Storage account created with `default_action = "Deny"` in network rules, preventing local Terraform from creating containers.

**Solution**:
Use `default_action = "Allow"` during initial deployment:

```hcl
***REMOVED*** modules/unity-catalog/main.tf
resource "azurerm_storage_account" "metastore" {
  name                     = local.metastore_storage_name
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  is_hns_enabled          = true
  
  network_rules {
    default_action = "Allow"  ***REMOVED*** Required for initial container creation
    bypass         = ["AzureServices"]
  }
}
```

**Post-Deployment Lockdown** (optional):
After successful deployment, you can manually update to deny default access and use Service Endpoint Policy for security.

---

***REMOVED******REMOVED*** Quick Reference Commands

***REMOVED******REMOVED******REMOVED*** Clean Destroy Sequence

**For New Deployments** (automatic cleanup):
```bash
terraform destroy
```

**For Existing Deployments** (manual cleanup):
```bash
***REMOVED*** 1. Start destroy
terraform destroy

***REMOVED*** 2. If SEP errors occur, remove from subnets
az network vnet subnet update \
  --resource-group <RG_NAME> \
  --vnet-name <VNET_NAME> \
  --name <SUBNET_NAME> \
  --remove serviceEndpointPolicies

***REMOVED*** 3. If NCC errors occur, remove from state
terraform state rm module.ncc.databricks_mws_network_connectivity_config.this

***REMOVED*** 4. If metastore errors occur, remove from state
terraform state rm module.unity_catalog.databricks_metastore_data_access.this
terraform state rm module.unity_catalog.databricks_metastore.this

***REMOVED*** 5. Complete destroy
terraform destroy
```

***REMOVED******REMOVED******REMOVED*** Verify Configuration

```bash
***REMOVED*** Validate Terraform configuration
terraform validate

***REMOVED*** Plan without applying
terraform plan

***REMOVED*** Check authentication
az account show
databricks auth env --profile account
```

***REMOVED******REMOVED******REMOVED*** State Management

```bash
***REMOVED*** List resources in state
terraform state list

***REMOVED*** Show specific resource
terraform state show 'module.unity_catalog.databricks_metastore.this'

***REMOVED*** Remove resource from state (does not delete in cloud)
terraform state rm 'resource.address'

***REMOVED*** Import existing resource
terraform import 'resource.address' 'resource-id'
```

---

***REMOVED******REMOVED*** Debugging Tips

***REMOVED******REMOVED******REMOVED*** Enable Detailed Logging

**Terraform Debug Logs**:
```bash
export TF_LOG=DEBUG
export TF_LOG_PATH="terraform-debug.log"
terraform apply
```

**Databricks Provider Logs**:
```bash
export DATABRICKS_DEBUG_TRUNCATE_BYTES=10000
export DATABRICKS_DEBUG_HEADERS=true
terraform apply 2>&1 | tee apply-debug.log
```

***REMOVED******REMOVED******REMOVED*** Check Resource State

**Azure Resources**:
```bash
***REMOVED*** List resource group contents
az resource list --resource-group <RG_NAME> --output table

***REMOVED*** Check workspace status
az databricks workspace show \
  --name <WORKSPACE_NAME> \
  --resource-group <RG_NAME>

***REMOVED*** Check storage account
az storage account show \
  --name <STORAGE_NAME> \
  --resource-group <RG_NAME>
```

**Databricks Resources**:
```bash
***REMOVED*** List metastores (requires account admin)
databricks metastores list --account-id <ACCOUNT_ID>

***REMOVED*** Show workspace details
databricks workspace get --workspace-id <WORKSPACE_ID>
```

---

***REMOVED******REMOVED*** Prevention Best Practices

***REMOVED******REMOVED******REMOVED*** 1. Set `force_destroy = true` for Metastores

```hcl
resource "databricks_metastore" "this" {
  provider      = databricks.account
  name          = var.metastore_name
  force_destroy = true  ***REMOVED*** Essential for clean destroy
}
```

***REMOVED******REMOVED******REMOVED*** 2. Use Conditional NSG Rules

```hcl
resource "azurerm_network_security_rule" "example" {
  count = var.enable_private_link ? 1 : 0  ***REMOVED*** Only for Private Link
  ***REMOVED*** ...
}
```

***REMOVED******REMOVED******REMOVED*** 3. Allow Initial Storage Access

```hcl
resource "azurerm_storage_account" "example" {
  network_rules {
    default_action = "Allow"  ***REMOVED*** Required initially
    bypass         = ["AzureServices"]
  }
}
```

***REMOVED******REMOVED******REMOVED*** 4. Tag All Resources

```hcl
locals {
  all_tags = merge(var.tags, {
    Owner     = var.tag_owner
    KeepUntil = var.tag_keepuntil
  })
}
```

***REMOVED******REMOVED******REMOVED*** 5. Test Destroy in Non-Production

```bash
***REMOVED*** Always test the full lifecycle
terraform apply
terraform destroy

***REMOVED*** If successful, apply to production
```

---

***REMOVED******REMOVED*** Getting Help

***REMOVED******REMOVED******REMOVED*** Documentation
- [Quickstart Guide](01-QUICKSTART.md)
- [Deployment Patterns](patterns/)
- [Module Reference](modules/)

***REMOVED******REMOVED******REMOVED*** External Resources
- [Azure Databricks Documentation](https://learn.microsoft.com/en-us/azure/databricks/)
- [Databricks Terraform Provider](https://registry.terraform.io/providers/databricks/databricks/latest/docs)
- [Azure Terraform Provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)

***REMOVED******REMOVED******REMOVED*** Support Channels
1. Check this troubleshooting guide first
2. Review checkpoint documents for similar issues
3. Check provider documentation for recent changes
4. Contact your platform team
