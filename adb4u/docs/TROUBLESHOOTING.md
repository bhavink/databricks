***REMOVED*** Troubleshooting Guide

**Last Updated**: 2026-01-10

This document contains solutions to common issues encountered during deployment, updates, and destruction of Azure Databricks workspaces.

---

***REMOVED******REMOVED*** Table of Contents

1. [Unity Catalog Destroy Issues](***REMOVED***unity-catalog-destroy-issues)
2. [Metastore Configuration](***REMOVED***metastore-configuration)
3. [Service Endpoint Policies](***REMOVED***service-endpoint-policies)
4. [NSG Rule Conflicts](***REMOVED***nsg-rule-conflicts)
5. [Authentication Issues](***REMOVED***authentication-issues)
6. [Storage Account Access](***REMOVED***storage-account-access)

---

***REMOVED******REMOVED*** Unity Catalog Destroy Issues

***REMOVED******REMOVED******REMOVED*** Issue: Cannot Delete Metastore Data Access

**Error Message**:
```
Error: cannot delete metastore data access: Storage credential 'proddb-metastore-access' 
cannot be deleted because it is configured as this metastore's root credential. 
Please update the metastore's root credential before attempting deletion.
```

**Root Cause**:
The metastore has a root storage credential attached, and Unity Catalog protects this credential from deletion to prevent data access issues.

**Solution**:
Set `force_destroy = true` in the metastore resource configuration.

**Implementation**:
```hcl
***REMOVED*** modules/unity-catalog/main.tf
resource "databricks_metastore" "this" {
  provider = databricks.account
  
  name         = var.metastore_name
  storage_root = "abfss://..."
  region       = var.location
  
  force_destroy = true  ***REMOVED*** CRITICAL: Allows clean destroy with root credential
  
  depends_on = [
    azurerm_role_assignment.metastore_contributor
  ]
}
```

**Important Notes**:
- ✅ **DO** set `force_destroy = true` in production deployments
- ❌ **DO NOT** add `lifecycle.ignore_changes = [force_destroy]` - it will prevent clean destroy
- ⚠️ `force_destroy = true` does not make deletion dangerous - it only allows Terraform to delete the metastore when you explicitly run `terraform destroy`
- 🔒 The metastore is still protected by requiring explicit destroy commands

**If Destroy Still Fails**:
If you encounter API validation errors during metastore update (e.g., `delta_sharing_recipient_token_lifetime_in_seconds` errors), remove the metastore from state:

```bash
terraform state rm 'module.unity_catalog.databricks_metastore_data_access.this[0]'
terraform state rm 'module.unity_catalog.databricks_metastore.this[0]'
terraform destroy -auto-approve
```

This removes the metastore from Terraform state (it remains in Databricks account) and allows clean destroy of all Azure infrastructure.

---

***REMOVED******REMOVED*** Metastore Configuration

***REMOVED******REMOVED******REMOVED*** Issue: Metastore Update Validation Error

**Error Message**:
```
Error: cannot update metastore: UpdateMetastore delta_sharing_recipient_token_lifetime_in_seconds 
can not be 0, which is infinite token lifetime.
```

**Root Cause**:
The Databricks API validates certain metastore parameters during updates. Setting `force_destroy` from `false` to `true` (or removing `lifecycle.ignore_changes`) triggers an update operation that fails API validation.

**Solution**:
1. **Prevention**: Set `force_destroy = true` from initial deployment
2. **If Already Deployed**: Remove metastore from state (see above)

**Code Template**:
```hcl
resource "databricks_metastore" "this" {
  provider      = databricks.account
  name          = var.metastore_name
  storage_root  = "abfss://..."
  region        = var.location
  force_destroy = true  ***REMOVED*** Set on initial creation
}
```

---

***REMOVED******REMOVED*** Service Endpoint Policies

***REMOVED******REMOVED******REMOVED*** Issue: SEP Cannot Be Deleted (Attached to Subnets)

**Error Message**:
```
Error: deleting Service Endpoint Policy: ServiceEndpointPolicyCannotBeDeletedIfReferencedBySubnet
Service Endpoint Policy cannot be deleted because it is in use with subnet(s).
```

**Root Cause**:
Azure prevents deletion of a Service Endpoint Policy while it's still referenced by subnets.

**Solution**:
Update subnets to remove SEP reference before destroying:

```bash
***REMOVED*** Step 1: Update subnets to remove SEP
terraform apply -target=module.networking.azurerm_subnet.public \
                -target=module.networking.azurerm_subnet.private \
                -auto-approve

***REMOVED*** Step 2: Destroy SEP and other resources
terraform destroy -auto-approve
```

**Code Fix** (preventative):
Ensure SEP is created/destroyed in correct order:
```hcl
resource "azurerm_subnet" "public" {
  ***REMOVED*** ...
  service_endpoint_policy_ids = var.enable_sep ? [azurerm_sep.this[0].id] : []
}
```

---

***REMOVED******REMOVED*** NSG Rule Conflicts

***REMOVED******REMOVED******REMOVED*** Issue: NSG Rule Priority Conflicts with Databricks

**Error Message**:
```
Error: Security rule AllowVnetInBound conflicts with rule 
Microsoft.Databricks-workspaces_UseOnly_databricks-worker-to-worker-inbound. 
Rules cannot have the same Priority and Direction.
```

**Root Cause**:
In Non-PL deployments, Databricks automatically creates NSG rules. Custom rules conflict with these.

**Solution**:
Make NSG rule creation conditional - only for Private Link deployments:

```hcl
***REMOVED*** modules/networking/nsg-rules.tf
resource "azurerm_network_security_rule" "inbound_vnet_to_vnet" {
  count = var.enable_private_link ? 1 : 0  ***REMOVED*** Only for Private Link
  
  name                        = "AllowVnetInBound"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "*"
  source_port_range          = "*"
  destination_port_range     = "*"
  source_address_prefix      = "VirtualNetwork"
  destination_address_prefix = "VirtualNetwork"
  resource_group_name        = var.resource_group_name
  network_security_group_name = var.nsg_name
}
```

**Rule Summary**:
- **Non-PL**: Databricks manages NSG rules automatically ✅
- **Private Link**: You must create NSG rules manually ✅

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
Export the tenant ID:

```bash
export DATABRICKS_AZURE_TENANT_ID="your-tenant-id"
export ARM_TENANT_ID="your-tenant-id"  ***REMOVED*** Also needed for Azure provider
```

**Provider Configuration**:
```hcl
***REMOVED*** deployments/non-pl/providers.tf
provider "databricks" {
  alias             = "account"
  host              = "https://accounts.azuredatabricks.net"
  account_id        = var.databricks_account_id
  azure_tenant_id   = var.databricks_azure_tenant_id
  azure_use_msi     = false
  azure_environment = "public"
}
```

**Environment Variables Required**:
```bash
***REMOVED*** Azure Authentication
export ARM_SUBSCRIPTION_ID="..."
export ARM_TENANT_ID="..."
export ARM_CLIENT_ID="..."        ***REMOVED*** If using service principal
export ARM_CLIENT_SECRET="..."    ***REMOVED*** If using service principal

***REMOVED*** Databricks Authentication
export DATABRICKS_ACCOUNT_ID="..."
export DATABRICKS_AZURE_TENANT_ID="$ARM_TENANT_ID"
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
  
  ***REMOVED*** Can be locked down post-deployment with firewall rules or SEP
}
```

**Post-Deployment Lockdown** (optional):
After successful deployment, you can manually update to:
```hcl
network_rules {
  default_action             = "Deny"
  virtual_network_subnet_ids = [var.public_subnet_id, var.private_subnet_id]
  bypass                     = ["AzureServices"]
}
```

---

***REMOVED******REMOVED*** Quick Reference: Common Commands

***REMOVED******REMOVED******REMOVED*** Clean Destroy Sequence
```bash
***REMOVED*** 1. Standard destroy
terraform destroy -auto-approve

***REMOVED*** 2. If metastore errors occur, remove from state
terraform state rm 'module.unity_catalog.databricks_metastore_data_access.this[0]'
terraform state rm 'module.unity_catalog.databricks_metastore.this[0]'
terraform destroy -auto-approve

***REMOVED*** 3. If SEP errors occur, update subnets first
terraform apply -target=module.networking.azurerm_subnet.public \
                -target=module.networking.azurerm_subnet.private \
                -auto-approve
terraform destroy -auto-approve
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
terraform state show 'module.unity_catalog.databricks_metastore.this[0]'

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
az resource list --resource-group rg-databricks-prod-eastus2 --output table

***REMOVED*** Check workspace status
az databricks workspace show --name proddb-workspace \
  --resource-group rg-databricks-prod-eastus2

***REMOVED*** Check storage account
az storage account show --name proddbmetastorekn7gcw \
  --resource-group rg-databricks-prod-eastus2
```

**Databricks Resources**:
```bash
***REMOVED*** List metastores (requires account admin)
databricks metastores list --account-id <account-id>

***REMOVED*** Show workspace details
databricks workspace get --workspace-id <workspace-id>
```

---

***REMOVED******REMOVED*** Prevention Best Practices

***REMOVED******REMOVED******REMOVED*** 1. **Always Set `force_destroy = true` for Metastores**
```hcl
resource "databricks_metastore" "this" {
  ***REMOVED*** ...
  force_destroy = true  ***REMOVED*** Essential for clean destroy
}
```

***REMOVED******REMOVED******REMOVED*** 2. **Conditional NSG Rules**
```hcl
resource "azurerm_network_security_rule" "example" {
  count = var.enable_private_link ? 1 : 0  ***REMOVED*** Only for PL
  ***REMOVED*** ...
}
```

***REMOVED******REMOVED******REMOVED*** 3. **Allow Initial Storage Access**
```hcl
resource "azurerm_storage_account" "example" {
  ***REMOVED*** ...
  network_rules {
    default_action = "Allow"  ***REMOVED*** Required initially
  }
}
```

***REMOVED******REMOVED******REMOVED*** 4. **Proper Dependency Management**
```hcl
resource "databricks_metastore" "this" {
  ***REMOVED*** ...
  depends_on = [
    azurerm_role_assignment.metastore_contributor  ***REMOVED*** Ensure RBAC is set
  ]
}
```

***REMOVED******REMOVED******REMOVED*** 5. **Tag All Resources**
```hcl
locals {
  all_tags = merge(var.tags, {
    Owner     = var.tag_owner
    KeepUntil = var.tag_keepuntil
  })
}
```

---

***REMOVED******REMOVED*** Getting Help

***REMOVED******REMOVED******REMOVED*** Internal Resources
- [Quickstart Guide](01-QUICKSTART.md)
- [Architecture Documentation](../README.md)
- [Checkpoint Documents](../checkpoint/)

***REMOVED******REMOVED******REMOVED*** External Resources
- [Azure Databricks Documentation](https://learn.microsoft.com/en-us/azure/databricks/)
- [Databricks Terraform Provider](https://registry.terraform.io/providers/databricks/databricks/latest/docs)
- [Azure Terraform Provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)

***REMOVED******REMOVED******REMOVED*** Support Channels
1. Check this troubleshooting guide first
2. Review checkpoint documents for similar issues
3. Check provider documentation for recent changes
4. Contact your platform team

---

**Document Version**: 1.0  
**Last Updated**: 2026-01-10  
**Maintainer**: Platform Engineering Team
