***REMOVED*** 06 - Troubleshooting Guide

> **Problem Solving**: Common issues, error messages, and solutions for Full Private deployments.

***REMOVED******REMOVED*** Quick Reference

```
💡 Most issues fall into 3 categories:
   1. Terraform/Azure errors (permissions, quotas)
   2. Network connectivity (Private Link, DNS)
   3. Unity Catalog (metastore, storage access)
```

---

***REMOVED******REMOVED*** Table of Contents

1. [Deployment Issues](***REMOVED***1-deployment-issues)
2. [Unity Catalog Issues](***REMOVED***2-unity-catalog-issues)
3. [Network Connectivity](***REMOVED***3-network-connectivity)
4. [Destroy Issues](***REMOVED***4-destroy-issues)
5. [Serverless Issues](***REMOVED***5-serverless-issues)
6. [Quick Commands](***REMOVED***6-quick-commands)

---

***REMOVED******REMOVED*** 1. Deployment Issues

***REMOVED******REMOVED******REMOVED*** **Issue: Terraform Plan Shows Many Changes After Apply**

**Symptoms**:
```
Plan: 0 to add, 21 to change, 0 to destroy
```

**Cause**: Tag updates or computed values that Terraform detects as changes

**Check**:
```bash
terraform plan -detailed-exitcode
***REMOVED*** Exit code 2 = changes pending
```

**Solution**:
- If only tag changes: Safe to apply
- If resource changes: Review carefully before applying

---

***REMOVED******REMOVED******REMOVED*** **Issue: NSG Rule Conflicts**

**Error**:
```
Error: Security rule AllowVnetInBound conflicts with rule 
Microsoft.Databricks-workspaces_UseOnly_databricks-worker-to-worker-inbound
```

**Cause**: Custom NSG rules created when `enable_public_network_access = true`

**Solution**: Custom NSG rules are only created when BOTH conditions met:
- `enable_private_link = true` 
- `enable_public_network_access = false`

**Check Configuration**:
```hcl
***REMOVED*** terraform.tfvars
enable_public_network_access = true  ***REMOVED*** Should be true for initial deployment
```

**Expected**: Databricks auto-creates NSG rules when public access enabled

---

***REMOVED******REMOVED******REMOVED*** **Issue: NCC Module Timeout**

**Error**:
```
Error: Post "https://accounts.azuredatabricks.net/api/2.0/accounts/.../
network-connectivity-configs/.../private-endpoint-rules": 
request timed out after 1m5s
```

**Cause**: ~~This should NOT happen anymore~~ - NCC module no longer creates PE rules

**Solution**: NCC PE rules are created manually (not by Terraform)

**Verify**:
```bash
***REMOVED*** Check NCC module code
cat modules/ncc/main.tf | grep databricks_mws_ncc_private_endpoint_rule
***REMOVED*** Should return NOTHING
```

**If You See PE Rules**: Update to latest code (they were removed)

---

***REMOVED******REMOVED*** 2. Unity Catalog Issues

***REMOVED******REMOVED******REMOVED*** **Issue: Cannot Delete Metastore During Destroy** ⚠️ COMMON

**Error**:
```
Error: cannot delete metastore data access: Storage credential 
'prodpl-metastore-access' cannot be deleted because it is configured 
as this metastore's root credential. Please update the metastore's 
root credential before attempting deletion.
```

**Cause**: Databricks API blocks deletion of root storage credential even with `force_destroy = true`

**Root Cause**: API validation happens before `force_destroy` is processed

**Solution**: Remove from Terraform state

```bash
cd deployments/full-private

***REMOVED*** Step 1: Remove metastore data access
terraform state rm 'module.unity_catalog.databricks_metastore_data_access.this[0]'

***REMOVED*** Step 2: Remove metastore
terraform state rm 'module.unity_catalog.databricks_metastore.this[0]'

***REMOVED*** Step 3: Retry destroy
terraform destroy
```

**Why This Works**: Metastore persists at account level (not deleted by Terraform anyway)

**Prevention**: This is expected behavior for metastores with data. Always use state removal for clean destroy.

---

***REMOVED******REMOVED******REMOVED*** **Issue: Metastore Already Exists**

**Error**:
```
Error: cannot create metastore: Metastore 'prod-pl-eastus2-metastore' 
already exists
```

**Cause**: Metastore persists from previous deployment

**Solution A**: Use existing metastore
```hcl
***REMOVED*** terraform.tfvars
create_metastore      = false
existing_metastore_id = "abc123-def456-ghi789"  ***REMOVED*** Get from Portal or previous output
```

**Solution B**: Rename metastore
```hcl
***REMOVED*** terraform.tfvars
metastore_name = "prod-pl-eastus2-metastore-v2"  ***REMOVED*** Add suffix
```

**Get Existing Metastore ID**:
```bash
***REMOVED*** Via Databricks CLI
databricks unity-catalog metastores list

***REMOVED*** Via Azure Portal
***REMOVED*** Databricks Account Console → Data → Metastores
```

---

***REMOVED******REMOVED******REMOVED*** **Issue: Storage Account Access Denied (403)**

**Error**:
```
Error: checking for existing Container "metastore" ... 
unexpected status 403 (403 This request is not authorized)
```

**Cause**: Storage account network rules blocking Terraform execution

**Solution**: Storage accounts must allow access during creation

**Verify Configuration** (`modules/unity-catalog/main.tf`):
```hcl
resource "azurerm_storage_account" "metastore" {
  ***REMOVED*** ...
  network_rules {
    default_action = "Allow"  ***REMOVED*** ✅ Required for initial creation
    bypass         = ["AzureServices"]
  }
}
```

**Post-Deployment Lockdown**: Lock down storage after serverless PE approved (see 04-SERVERLESS-SETUP.md)

---

***REMOVED******REMOVED*** 3. Network Connectivity

***REMOVED******REMOVED******REMOVED*** **Issue: Workspace Not Accessible**

**Symptoms**: Cannot access workspace URL, browser timeout

**Check 1: Public Access Setting**
```bash
terraform output deployment_summary
***REMOVED*** Check: public_access = "Enabled" or "Disabled"
```

**If Disabled**:
- Requires VPN/Bastion/Jump Box
- Or set `enable_public_network_access = true` and re-apply

**Check 2: IP Access Lists**
```hcl
***REMOVED*** terraform.tfvars
enable_ip_access_lists = true
allowed_ip_ranges = ["YOUR_IP/32"]  ***REMOVED*** ⚠️ Must include YOUR IP
```

**Find Your IP**:
```bash
curl ifconfig.me
```

**Solution**: Add your IP to allowed ranges or disable IP ACLs for testing

---

***REMOVED******REMOVED******REMOVED*** **Issue: Classic Cluster Fails to Start**

**Symptoms**:
```
Cluster failed to start: Network connectivity issue
```

**Check 1: Private Endpoints Created**
```bash
terraform output private_endpoint_ids
***REMOVED*** Should show 10 endpoints
```

**Check 2: DNS Resolution**
```bash
***REMOVED*** From a VM in the VNet
nslookup <storage-account-name>.dfs.core.windows.net
***REMOVED*** Should resolve to private IP (10.x.x.x)
```

**Check 3: NSG Rules**
```bash
***REMOVED*** Azure Portal → NSG → Inbound/Outbound Rules
***REMOVED*** Should see Databricks-managed rules
```

**Solution**: Verify all Private Endpoints are "Approved" in Azure Portal

---

***REMOVED******REMOVED******REMOVED*** **Issue: Private Endpoint Shows "Pending"**

**Cause**: Should NOT happen - Private Endpoints to customer resources are auto-approved

**Check**: Are you looking at NCC endpoints (for serverless)?

**NCC Endpoints** (Manual):
- Created by Databricks (not Terraform)
- Require manual approval
- See: [04-SERVERLESS-SETUP.md](04-SERVERLESS-SETUP.md)

**VNet Endpoints** (Auto):
- Created by Terraform
- Auto-approved (same tenant)
- Should show "Approved" immediately

---

***REMOVED******REMOVED*** 4. Destroy Issues

***REMOVED******REMOVED******REMOVED*** **Issue: Cannot Delete NCC (Attached to Workspace)**

**Error**:
```
Error: cannot delete mws network connectivity config: 
Network Connectivity Config xxx is unable to be deleted because 
it is attached to one or more workspaces
```

**Cause**: NCC binding must be deleted before NCC config

**Solution**: Remove from state
```bash
cd deployments/full-private

***REMOVED*** Remove NCC binding
terraform state rm 'module.ncc[0].databricks_mws_ncc_binding.this'

***REMOVED*** Remove NCC config
terraform state rm 'module.ncc[0].databricks_mws_network_connectivity_config.this'

***REMOVED*** Retry destroy
terraform destroy
```

**Why**: NCC persists at account level (reusable across workspaces)

---

***REMOVED******REMOVED******REMOVED*** **Issue: Private Endpoint Deletion Timeout**

**Symptoms**: Destroy hangs for 10+ minutes on Private Endpoint deletion

**Cause**: Azure sometimes slow to release Private Endpoint connections

**Solution**: Wait (can take up to 15 minutes) or use Portal

**Via Portal**:
1. Azure Portal → Private Link Center
2. Find pending deletions
3. Manually delete if stuck

**Force Removal**:
```bash
***REMOVED*** If destroy stuck > 20 minutes
Ctrl+C  ***REMOVED*** Cancel Terraform

***REMOVED*** Remove from state
terraform state rm 'module.private_endpoints.azurerm_private_endpoint.<NAME>'

***REMOVED*** Manually delete in Portal
***REMOVED*** Then retry destroy
terraform destroy
```

---

***REMOVED******REMOVED******REMOVED*** **Issue: Storage Account Deletion Fails (Data Present)**

**Error**:
```
Error: deleting Storage Account: storage account cannot be deleted 
because it contains data
```

**Cause**: Storage account has active containers/blobs (Unity Catalog schemas)

**Solution A**: Force delete via Azure CLI
```bash
az storage account delete \
  --name <storage-account-name> \
  --resource-group <rg-name> \
  --yes
```

**Solution B**: Remove from state
```bash
terraform state rm 'module.unity_catalog.azurerm_storage_account.metastore[0]'
terraform state rm 'module.unity_catalog.azurerm_storage_account.external[0]'

***REMOVED*** Manually delete in Portal after backing up data
```

**Prevention**: Backup critical data before `terraform destroy`

---

***REMOVED******REMOVED*** 5. Serverless Issues

***REMOVED******REMOVED******REMOVED*** **Issue: SQL Warehouse Fails to Start**

**Symptoms**:
```
Error: Unable to connect to metastore
Error: Network connectivity issue
```

**Check 1: NCC Attached**
```bash
terraform output ncc_id
***REMOVED*** Should NOT be null
```

**If NULL**:
```hcl
***REMOVED*** terraform.tfvars
enable_ncc = true
```
```bash
terraform apply
```

**Check 2: Serverless Private Link Enabled**
- Databricks UI → Settings → Network → Serverless compute
- Should show "Enabled"

**Check 3: Private Endpoint Approval**
- Azure Portal → Storage Accounts → Networking → Private endpoint connections
- All connections from Databricks should be "Approved"

**Solution**: Follow [04-SERVERLESS-SETUP.md](04-SERVERLESS-SETUP.md) step-by-step

---

***REMOVED******REMOVED******REMOVED*** **Issue: Serverless Works But No Data**

**Symptoms**: SQL Warehouse runs but queries return 0 rows

**Check 1: Permissions**
```sql
-- Run in SQL Warehouse
SHOW GRANTS ON CATALOG <catalog_name>;
SHOW GRANTS ON SCHEMA <schema_name>;
```

**Check 2: Storage Access**
- Verify Access Connector has "Storage Blob Data Contributor" on UC storage
- Azure Portal → Storage Account → Access Control (IAM)

**Solution**: Add missing permissions
```bash
***REMOVED*** Via Azure CLI
az role assignment create \
  --assignee <access-connector-principal-id> \
  --role "Storage Blob Data Contributor" \
  --scope <storage-account-id>
```

---

***REMOVED******REMOVED*** 6. Quick Commands

***REMOVED******REMOVED******REMOVED*** **State Management**

**List State Resources**:
```bash
terraform state list
```

**Remove Specific Resource**:
```bash
terraform state rm '<resource_address>'
```

**Show Resource State**:
```bash
terraform state show '<resource_address>'
```

***REMOVED******REMOVED******REMOVED*** **Clean Destroy Sequence**

**Standard Destroy**:
```bash
terraform destroy
```

**Force Clean Destroy** (if errors):
```bash
***REMOVED*** 1. Remove problematic UC resources
terraform state rm 'module.unity_catalog.databricks_metastore_data_access.this[0]'
terraform state rm 'module.unity_catalog.databricks_metastore.this[0]'

***REMOVED*** 2. Remove NCC resources (if attached)
terraform state rm 'module.ncc[0].databricks_mws_ncc_binding.this'
terraform state rm 'module.ncc[0].databricks_mws_network_connectivity_config.this'

***REMOVED*** 3. Retry destroy
terraform destroy

***REMOVED*** 4. If still errors, manual Portal cleanup + state removal
```

***REMOVED******REMOVED******REMOVED*** **Validation Commands**

**Check Terraform State**:
```bash
terraform plan -detailed-exitcode
***REMOVED*** Exit 0 = no changes
***REMOVED*** Exit 1 = error
***REMOVED*** Exit 2 = changes pending
```

**Validate Configuration**:
```bash
terraform validate
```

**Check Outputs**:
```bash
terraform output
terraform output -json | jq .
```

***REMOVED******REMOVED******REMOVED*** **Debugging**

**Enable Terraform Debug Logging**:
```bash
export TF_LOG=DEBUG
export TF_LOG_PATH=./terraform-debug.log
terraform apply
```

**Check Databricks Provider Version**:
```bash
terraform version
***REMOVED*** Should show databricks provider >= 1.29.0
```

**Test Network Connectivity** (from VNet VM):
```bash
***REMOVED*** Test workspace
curl -I https://<workspace-url>

***REMOVED*** Test storage (should resolve to private IP)
nslookup <storage-account>.dfs.core.windows.net
```

---

***REMOVED******REMOVED*** 7. Common Error Messages

***REMOVED******REMOVED******REMOVED*** **Error Dictionary**

| Error Message | Likely Cause | Quick Fix |
|---------------|--------------|-----------|
| `Storage credential cannot be deleted` | UC metastore root credential | `terraform state rm` (see Section 2) |
| `NSG rule conflicts` | Public access enabled + custom rules | Set `enable_public_network_access = true` |
| `NCC cannot be deleted` | Attached to workspace | `terraform state rm` NCC resources |
| `403 unauthorized` | Storage firewall or missing permissions | Check `default_action = "Allow"` |
| `Metastore already exists` | Previous deployment | Use existing or rename |
| `Workspace not accessible` | Private Link + no VPN/Bastion | Enable public access or use VPN |
| `NCC timeout` | ~~Should not happen~~ Old code | Verify NCC module has no PE rules |
| `Private Endpoint pending` | ~~Should not happen for VNet PE~~ | Check if NCC PE (manual approval) |

---

***REMOVED******REMOVED*** 8. Getting More Help

***REMOVED******REMOVED******REMOVED*** **Check Documentation**

1. [01-ARCHITECTURE.md](01-ARCHITECTURE.md) - Understand system design
2. [04-SERVERLESS-SETUP.md](04-SERVERLESS-SETUP.md) - Serverless specific issues
3. [README.md](README.md) - Documentation index

***REMOVED******REMOVED******REMOVED*** **Review Deployment Summary**

```bash
terraform output deployment_summary
terraform output next_steps
```

***REMOVED******REMOVED******REMOVED*** **Check Implementation Notes**

```bash
cat ../../../checkpoint/FULL-PRIVATE-IMPLEMENTATION-COMPLETE.md
```

***REMOVED******REMOVED******REMOVED*** **Azure/Databricks Support**

**Azure Documentation**:
- [Private Link Troubleshooting](https://learn.microsoft.com/en-us/azure/private-link/troubleshoot-private-link-connectivity)
- [NSG Flow Logs](https://learn.microsoft.com/en-us/azure/network-watcher/network-watcher-nsg-flow-logging-overview)

**Databricks Documentation**:
- [Private Link Troubleshooting](https://docs.databricks.com/en/security/network/classic/private-link-troubleshooting.html)
- [Unity Catalog Troubleshooting](https://docs.databricks.com/en/data-governance/unity-catalog/troubleshooting.html)

---

***REMOVED******REMOVED*** 9. Prevention Best Practices

***REMOVED******REMOVED******REMOVED*** **Before Deployment**

- ✅ Verify Azure quotas (Private Endpoints, Public IPs)
- ✅ Confirm Databricks account ID and permissions
- ✅ Review `terraform.tfvars.example` carefully
- ✅ Use `terraform plan` before `apply`

***REMOVED******REMOVED******REMOVED*** **During Deployment**

- ✅ Monitor Terraform output for warnings
- ✅ Don't interrupt `terraform apply` mid-execution
- ✅ Note down workspace URL and outputs immediately

***REMOVED******REMOVED******REMOVED*** **Before Destroy**

- ✅ **Backup Unity Catalog data** (critical!)
- ✅ Export notebooks and cluster configs
- ✅ Document any manual configurations
- ✅ Expect UC metastore state removal (normal)

***REMOVED******REMOVED******REMOVED*** **After Deployment**

- ✅ Test classic cluster immediately
- ✅ Verify Unity Catalog access
- ✅ Document any manual changes made
- ✅ Consider locking down public access (if not done)

---

**Most Common Issues**:
1. ⚠️ UC metastore deletion → Use `terraform state rm`
2. ⚠️ NCC attached → Remove from state before destroy
3. ⚠️ Serverless not working → Manual setup required (see 04-SERVERLESS-SETUP.md)

**Last Updated**: 2026-01-12
