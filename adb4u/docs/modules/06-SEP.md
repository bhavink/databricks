***REMOVED*** Service Endpoint Policy (SEP) Module

> **Control storage egress** from your VNet by allow-listing only approved Azure Storage accounts. Prevent data exfiltration via unauthorized storage access.

---

***REMOVED******REMOVED*** Overview

The Service Endpoint Policy module restricts storage access from your Databricks VNet to only explicitly approved storage accounts. This prevents accidental or malicious data exfiltration by ensuring compute can only write to known, trusted storage locations.

***REMOVED******REMOVED******REMOVED*** What It Does

**Security Control:**
- ✅ **Allow** access to DBFS root storage
- ✅ **Allow** access to Unity Catalog storage
- ✅ **Allow** access to customer storage accounts (via allow-list)
- ✅ **Allow** access to Databricks system storage (via alias)
- ❌ **Block** access to all other storage accounts

***REMOVED******REMOVED******REMOVED*** Key Features

✅ **Egress Control** - Prevent data leaving via unauthorized storage  
✅ **Automatic** - DBFS and UC storage automatically included  
✅ **Flexible** - Add custom storage accounts via list  
✅ **System Storage** - Databricks system accounts via alias  
✅ **BYOV Support** - Works with bring-your-own VNet  

⚠️ **Applies to**: Classic compute only (not serverless)

---

***REMOVED******REMOVED*** Architecture

***REMOVED******REMOVED******REMOVED*** Component Overview

```
┌──────────────────────────────────────────────────────┐
│           Your Databricks VNet                        │
│                                                       │
│  ┌─────────────────────────────────────────────┐    │
│  │  Classic Cluster (Spark Workers)            │    │
│  │  Trying to access storage...                │    │
│  └───────────────────┬─────────────────────────┘    │
│                      │                               │
│  ┌───────────────────▼───────────────────────┐      │
│  │  Subnets with SEP Attached                │      │
│  │  ├─ Public Subnet  → SEP                  │      │
│  │  └─ Private Subnet → SEP                  │      │
│  └───────────────────┬───────────────────────┘      │
└────────────────────┼─┼────────────────────────────────┘
                     │ │
        Service Endpoint (Azure backbone)
                     │ │
      ┌──────────────▼─▼───────────────┐
      │ Service Endpoint Policy (SEP)  │
      │                                 │
      │ Allowed Storage Accounts:      │
      │ ✅ DBFS root storage           │
      │ ✅ UC metastore storage        │
      │ ✅ UC external storage         │
      │ ✅ Databricks system storage   │
      │ ✅ Custom storage accounts     │
      │                                 │
      │ Denied:                         │
      │ ❌ All other storage accounts  │
      └─────────────────────────────────┘
                     │
                     ▼
        ┌─────────────────────────┐
        │  Approved Storage Only  │
        │  (Access Granted)       │
        └─────────────────────────┘
```

***REMOVED******REMOVED******REMOVED*** How It Works

1. **Policy Creation** - SEP created with allow-list of storage accounts
2. **Subnet Association** - SEP attached to Databricks subnets
3. **Traffic Evaluation** - Outbound storage traffic evaluated against policy
4. **Allow/Deny Decision** - Only allow-listed accounts permitted

---

***REMOVED******REMOVED*** Configuration

***REMOVED******REMOVED******REMOVED*** Basic Usage

Enable SEP with automatic storage accounts:

```hcl
***REMOVED*** terraform.tfvars
enable_service_endpoint_policy = true  ***REMOVED*** Enabled by default

***REMOVED*** Automatically includes:
***REMOVED*** - DBFS root storage
***REMOVED*** - UC metastore storage
***REMOVED*** - UC external storage
***REMOVED*** - Databricks system storage (via alias)
```

***REMOVED******REMOVED******REMOVED*** Add Custom Storage Accounts

```hcl
enable_service_endpoint_policy = true

additional_storage_account_ids = [
  "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.Storage/storageAccounts/customer-storage-1",
  "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.Storage/storageAccounts/customer-storage-2"
]
```

***REMOVED******REMOVED******REMOVED*** Disable SEP (Not Recommended)

```hcl
enable_service_endpoint_policy = false

***REMOVED*** ⚠️ Warning: Disabling SEP removes egress control.
***REMOVED*** Compute can access ANY storage account.
```

---

***REMOVED******REMOVED*** Module Structure

```
modules/service-endpoint-policy/
├── main.tf       ***REMOVED*** SEP resource, policy definitions
├── variables.tf  ***REMOVED*** Configuration options
└── outputs.tf    ***REMOVED*** SEP ID, allowed accounts
```

***REMOVED******REMOVED******REMOVED*** Key Resources

- `azurerm_subnet_service_endpoint_storage_policy` - SEP with allow-list
- Policy definitions for each storage type
- Subnet updates to attach SEP (via `null_resource` for graceful handling)

---

***REMOVED******REMOVED*** Practical Usage

***REMOVED******REMOVED******REMOVED*** Deployment Workflow

**1. Enable in terraform.tfvars**

```hcl
enable_service_endpoint_policy = true

***REMOVED*** Add custom storage if needed
additional_storage_account_ids = [
  "/subscriptions/.../storageAccounts/my-data-lake"
]
```

**2. Deploy**

```bash
terraform apply
```

**3. Verify**

```bash
terraform output service_endpoint_policy

***REMOVED*** Output:
{
  "allowed_storage_ids" = [
    "/subscriptions/.../storageAccounts/dbstorageXXX",      ***REMOVED*** DBFS
    "/subscriptions/.../storageAccounts/proddbmetastore",   ***REMOVED*** UC metastore
    "/subscriptions/.../storageAccounts/proddbexternal",    ***REMOVED*** UC external
    "/subscriptions/.../storageAccounts/my-data-lake"       ***REMOVED*** Custom
  ]
  "id" = "/subscriptions/.../serviceEndpointPolicies/..."
  "name" = "proddb-sep-storage-xxxxx"
}
```

***REMOVED******REMOVED******REMOVED*** Validation Checklist

After deployment, verify:

- [ ] SEP created with correct storage accounts
- [ ] Subnets have SEP attached
- [ ] Cluster can access DBFS (allowed)
- [ ] Cluster can access UC storage (allowed)
- [ ] Cluster cannot access unauthorized storage (blocked)

***REMOVED******REMOVED******REMOVED*** Testing SEP

**Test Allowed Access (Should Work):**

```python
***REMOVED*** Access DBFS (allowed)
dbutils.fs.ls("dbfs:/")

***REMOVED*** Access Unity Catalog (allowed)
spark.sql("SELECT * FROM catalog.schema.table LIMIT 10").show()

***REMOVED*** Access custom storage (if added to allow-list)
df = spark.read.parquet("abfss://container@customstorage.dfs.core.windows.net/data/")
```

**Test Blocked Access (Should Fail):**

```python
***REMOVED*** Try to access unauthorized storage account
df = spark.read.parquet("abfss://container@unauthorizedstorage.dfs.core.windows.net/data/")

***REMOVED*** Expected error:
***REMOVED*** "This request is not authorized to perform this operation using this permission"
***REMOVED*** OR "Forbidden"
```

---

***REMOVED******REMOVED*** How-To Guides

***REMOVED******REMOVED******REMOVED*** Add Storage Account After Deployment

```hcl
***REMOVED*** Update terraform.tfvars
additional_storage_account_ids = [
  "/subscriptions/.../storageAccounts/existing-storage",
  "/subscriptions/.../storageAccounts/new-storage"  ***REMOVED*** Add this
]

***REMOVED*** Apply changes
terraform apply
```

***REMOVED******REMOVED******REMOVED*** Remove Storage Account

```hcl
***REMOVED*** Remove from list in terraform.tfvars
additional_storage_account_ids = [
  "/subscriptions/.../storageAccounts/keep-this-one"
  ***REMOVED*** Removed: "/subscriptions/.../storageAccounts/remove-this-one"
]

terraform apply
```

***REMOVED******REMOVED******REMOVED*** BYOV with SEP

When using existing VNet:

```hcl
use_existing_network = true
enable_service_endpoint_policy = true

***REMOVED*** SEP will be attached to existing subnets
***REMOVED*** Ensure existing subnets have Service Endpoints enabled:
***REMOVED*** - Microsoft.Storage
***REMOVED*** - Microsoft.KeyVault
```

---

***REMOVED******REMOVED*** Troubleshooting

***REMOVED******REMOVED******REMOVED*** Issue: "Service endpoint policy definition contains invalid resource name"

**Cause**: Workspace not enabled for SEP support (created before July 14, 2025).

**Solution**: Contact Databricks account team to enable SEP support.

```
Workspaces created on or after July 14, 2025 support SEP by default.
For older workspaces, request enablement from Databricks.
```

***REMOVED******REMOVED******REMOVED*** Issue: "Cannot access UC storage after enabling SEP"

**Cause**: UC storage not in SEP allow-list.

**Solution**: Check SEP includes UC storage:

```bash
terraform output service_endpoint_policy | grep storageAccounts
```

UC storage should be automatically included. If missing, report as bug.

***REMOVED******REMOVED******REMOVED*** Issue: "SEP cannot be deleted because it is in use"

**Cause**: SEP still attached to subnets.

**Solution**: Module handles this automatically via destroy provisioners. If issues persist:

```bash
***REMOVED*** Manual cleanup (only if destroy fails)
az network vnet subnet update \
  --resource-group <RG_NAME> \
  --vnet-name <VNET_NAME> \
  --name <SUBNET_NAME> \
  --remove serviceEndpointPolicies

terraform destroy
```

---

***REMOVED******REMOVED*** Best Practices

✅ **DO:**
- Enable SEP by default for all deployments
- Add customer storage accounts explicitly
- Test access before production use
- Document allowed storage accounts
- Use resource IDs (not storage account names)

❌ **DON'T:**
- Disable SEP unless absolutely necessary
- Add storage accounts you don't need
- Use storage account names (use full resource IDs)
- Forget to add custom storage before using it

---

***REMOVED******REMOVED*** Important Notes

***REMOVED******REMOVED******REMOVED*** Scope Limitations

**SEP Applies To:**
- ✅ Classic clusters (interactive, job, all-purpose)
- ✅ Data written to external storage
- ✅ Data read from external storage

**SEP Does NOT Apply To:**
- ❌ Serverless compute (different connectivity model)
- ❌ Control plane operations
- ❌ Databricks-to-Databricks communication

***REMOVED******REMOVED******REMOVED*** Serverless Connectivity

For serverless compute, use different approaches:
- **Service Endpoints**: Configure storage firewall with serverless subnets
- **Private Link**: Use NCC with private endpoints

See: [Serverless Setup Guide](../guides/01-SERVERLESS-SETUP.md)

***REMOVED******REMOVED******REMOVED*** Databricks System Storage

The SEP includes Databricks system storage accounts via alias:
```
/services/Azure/Databricks
```

This allows access to:
- Artifact blob storage (cluster libraries)
- System tables storage
- Log blob storage

**Requirement**: Only works for workspaces created on/after July 14, 2025.

---

***REMOVED******REMOVED*** Cost Considerations

- **Service Endpoint**: Free (no Azure charges)
- **SEP**: Free (no additional cost)
- **Traffic**: Stays on Azure backbone (no egress fees)

**Total cost**: $0

---

***REMOVED******REMOVED*** References

**Azure Documentation:**
- [Service Endpoints](https://learn.microsoft.com/en-us/azure/virtual-network/virtual-network-service-endpoints-overview)
- [Service Endpoint Policies](https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/service-endpoints)
- [Data Exfiltration Prevention](https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/service-endpoints***REMOVED***configure-a-service-endpoint-policy)

**Terraform Providers:**
- [azurerm_subnet_service_endpoint_storage_policy](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/subnet_service_endpoint_storage_policy)
- [azurerm_subnet](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/subnet)

**Related Guides:**
- [Networking Module](01-NETWORKING.md)
- [Serverless Setup](../guides/01-SERVERLESS-SETUP.md)
- [Troubleshooting](../04-TROUBLESHOOTING.md)
