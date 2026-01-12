***REMOVED*** 04 - Serverless Compute Setup Guide

> **Enable Databricks Serverless** with private connectivity using Private Link or Firewall rules.

***REMOVED******REMOVED*** Quick Reference

```
📦 Prerequisites: NCC attached, Classic clusters working
⏱️  Setup Time: 15-30 minutes (includes approval workflow)
🔐 Manual Steps: Azure Portal approval required
```

---

***REMOVED******REMOVED*** Table of Contents

1. [Prerequisites](***REMOVED***1-prerequisites)
2. [Understanding Serverless Connectivity](***REMOVED***2-understanding-serverless-connectivity)
3. [Option A: Private Link Setup](***REMOVED***3-option-a-private-link-setup-recommended)
4. [Option B: Firewall Setup](***REMOVED***4-option-b-firewall-setup-hybrid)
5. [Testing Serverless](***REMOVED***5-testing-serverless)
6. [Lock Down Storage](***REMOVED***6-lock-down-storage)
7. [Troubleshooting](***REMOVED***7-troubleshooting)

---

***REMOVED******REMOVED*** 1. Prerequisites

***REMOVED******REMOVED******REMOVED*** **Verify NCC Status**

```bash
cd deployments/full-private
terraform output ncc_id
```

**Expected**:
- NCC ID displayed (e.g., `3951e460-b6fe-4022-82cb-b56eef48b90d`)
- If NULL: Set `enable_ncc = true` in `terraform.tfvars` and run `terraform apply`

***REMOVED******REMOVED******REMOVED*** **Verify Classic Clusters**

Before enabling serverless, ensure classic clusters work:

1. Go to workspace URL (check `terraform output workspace_url`)
2. Create a classic cluster
3. Run a test notebook
4. Query Unity Catalog: `SELECT * FROM system.information_schema.catalogs`

**Why**: Validates that Private Endpoints, Unity Catalog, and network configuration are correct.

---

***REMOVED******REMOVED*** 2. Understanding Serverless Connectivity

***REMOVED******REMOVED******REMOVED*** **Classic vs. Serverless Storage Access**

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '***REMOVED***e1e1e1'}}}%%
graph TB
    subgraph "Classic Clusters - WORKS IMMEDIATELY"
        CLUSTER["Classic Cluster<br/>Runs in Customer VNet"]
        VNET_PE["VNet Private Endpoints<br/>Auto-Approved"]
        STORAGE1["Storage Accounts<br/>DBFS + UC"]
    end
    
    subgraph "Serverless Compute - REQUIRES SETUP"
        SERVERLESS["Serverless Compute<br/>Runs in Databricks VNet"]
        NCC["Network Connectivity Config<br/>NCC"]
        NCC_PE["NCC Private Endpoints<br/>Manual Approval Required"]
        STORAGE2["Storage Accounts<br/>DBFS + UC"]
    end
    
    CLUSTER -->|Uses| VNET_PE
    VNET_PE -->|Auto-Approved| STORAGE1
    
    SERVERLESS -->|Uses| NCC
    NCC -->|Creates| NCC_PE
    NCC_PE -.->|Customer Approves| STORAGE2
    
    style CLUSTER fill:***REMOVED***569A31,color:***REMOVED***fff
    style SERVERLESS fill:***REMOVED***FF3621,color:***REMOVED***fff
    style NCC_PE fill:***REMOVED***FF9900,color:***REMOVED***000
```

***REMOVED******REMOVED******REMOVED*** **Key Differences**

| Aspect | Classic Clusters | Serverless Compute |
|--------|------------------|-------------------|
| **Where Runs** | Customer VNet | Databricks SaaS VNet |
| **Storage Access** | VNet Private Endpoints | NCC Private Endpoints |
| **Approval** | Auto-approved (same tenant) | Manual (cross-account) |
| **Setup** | Terraform | Azure Portal + Databricks |
| **Terraform Managed** | ✅ Yes | ❌ No (manual) |

---

***REMOVED******REMOVED*** 3. Option A: Private Link Setup (RECOMMENDED)

**Best For**: Air-gapped deployments, maximum security

***REMOVED******REMOVED******REMOVED*** **3.1 Enable Serverless Private Link**

**Via Databricks UI**:

1. Go to your workspace
2. Click **Settings** (gear icon, bottom left)
3. Navigate to **Network** tab
4. Find **Serverless compute for notebooks**
5. Click **Configure**
6. Select **Enable private connectivity**
7. Click **Save**

**What Happens**:
- Databricks creates Private Endpoint connections from its SaaS environment to your storage accounts
- Connections appear as "Pending" in Azure Portal
- **You must approve them manually**

***REMOVED******REMOVED******REMOVED*** **3.2 Approve Private Endpoint Connections**

**For Each Storage Account** (DBFS, UC Metastore, UC External):

***REMOVED******REMOVED******REMOVED******REMOVED*** **Step 1: Navigate to Storage Account**

```bash
***REMOVED*** Get storage account names from Terraform
terraform output metastore_storage_account_name
terraform output external_location_storage_account_name
***REMOVED*** DBFS storage is in workspace managed resource group
```

Azure Portal:
1. Search for storage account name
2. Click on the storage account

***REMOVED******REMOVED******REMOVED******REMOVED*** **Step 2: View Pending Connections**

1. In left menu, go to **Networking**
2. Click **Private endpoint connections** tab
3. Look for connections with:
   - **Status**: Pending
   - **Source**: From Databricks (different subscription)
   - **Target**: blob or dfs subresource

***REMOVED******REMOVED******REMOVED******REMOVED*** **Step 3: Approve Connection**

1. Select the pending connection(s)
2. Click **Approve** button at top
3. Add description (e.g., "Databricks Serverless Access")
4. Click **Yes** to confirm

**Repeat for ALL storage accounts**: DBFS, UC Metastore, UC External

***REMOVED******REMOVED******REMOVED******REMOVED*** **Visual Guide**

```
Azure Portal Flow:

Storage Account → Networking → Private endpoint connections
                                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Name: pe-serverless-databricks-abc123                       │
│ Connection state: Pending approval                          │
│ Source: Databricks (subscription: xxx-xxx-xxx)              │
│ Target sub-resource: blob                                   │
│                                                              │
│ [Approve]  [Reject]                                          │
└─────────────────────────────────────────────────────────────┘
```

***REMOVED******REMOVED******REMOVED******REMOVED*** **Step 4: Verify Approval**

After approval, connection state changes to:
- **Status**: Approved
- **Provisioning State**: Succeeded

**Expected**:
- 6 connections per storage account (2 each: blob + dfs)
- 3 storage accounts = 18 total connections

**Actual**:
- Databricks may create fewer (optimized for usage)
- At minimum: 1 connection per storage account

***REMOVED******REMOVED******REMOVED*** **3.3 Wait for Propagation**

**Time**: 5-10 minutes

**Check Status**:
1. Databricks UI → Settings → Network
2. Serverless compute section should show "Enabled"

---

***REMOVED******REMOVED*** 4. Option B: Firewall Setup (HYBRID)

**Best For**: Hybrid connectivity, less restrictive than air-gapped

***REMOVED******REMOVED******REMOVED*** **4.1 Get Serverless Subnet IDs**

**Via Databricks API**:

```bash
***REMOVED*** Get workspace ID
WORKSPACE_ID=$(terraform output -raw workspace_id_numeric)

***REMOVED*** Get serverless subnet IDs
curl -X GET \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  "https://<YOUR_WORKSPACE>.azuredatabricks.net/api/2.0/sql/config/warehouses"
```

**Expected Output**: List of subnet resource IDs used by serverless compute

***REMOVED******REMOVED******REMOVED*** **4.2 Add Subnets to Storage Firewall**

**For Each Storage Account**:

1. Azure Portal → Storage Account → **Networking**
2. **Firewalls and virtual networks** tab
3. Select **Enabled from selected virtual networks and IP addresses**
4. Under **Virtual networks**:
   - Click **+ Add existing virtual network**
   - Select the serverless subnet IDs from Databricks
5. Click **Save**

**Repeat for**: DBFS, UC Metastore, UC External storage accounts

***REMOVED******REMOVED******REMOVED*** **4.3 Verify Connectivity**

1. Create SQL Warehouse (see Section 5)
2. Run test query
3. If fails, review firewall rules

---

***REMOVED******REMOVED*** 5. Testing Serverless

***REMOVED******REMOVED******REMOVED*** **5.1 Create SQL Warehouse**

1. Databricks UI → **SQL Warehouses**
2. Click **Create SQL Warehouse**
3. Configure:
   - **Name**: `test-serverless-warehouse`
   - **Cluster size**: X-Small (for testing)
   - **Auto stop**: 10 minutes
4. Click **Create**

**Wait**: 2-5 minutes for warehouse to start

***REMOVED******REMOVED******REMOVED*** **5.2 Test Query**

SQL Warehouse Query Editor:

```sql
-- Test Unity Catalog connectivity
SELECT * FROM system.information_schema.catalogs;

-- Test external location access
SELECT * FROM <your_catalog>.<your_schema>.<your_table> LIMIT 10;
```

**Expected**: Queries succeed, data returned

**If Fails**: See [Troubleshooting](***REMOVED***7-troubleshooting)

***REMOVED******REMOVED******REMOVED*** **5.3 Test Serverless Notebook** (Optional)

1. Create new notebook
2. Select **Serverless** as compute
3. Run:

```python
***REMOVED*** Test Unity Catalog
spark.sql("SHOW CATALOGS").show()

***REMOVED*** Test data access
df = spark.table("system.information_schema.catalogs")
display(df)
```

**Expected**: Notebook runs successfully

---

***REMOVED******REMOVED*** 6. Lock Down Storage

**CRITICAL**: After Private Endpoints approved and serverless tested, lock down storage for security.

***REMOVED******REMOVED******REMOVED*** **6.1 Disable Public Network Access**

**For Each Storage Account** (DBFS, UC Metastore, UC External):

1. Azure Portal → Storage Account → **Networking**
2. **Firewalls and virtual networks** tab
3. Select **Disabled** under "Public network access"
4. Click **Save**

**Warning**: This makes storage accessible ONLY via Private Endpoints. Ensure:
- Classic cluster connectivity tested ✅
- Serverless connectivity tested ✅
- All required PE connections approved ✅

***REMOVED******REMOVED******REMOVED*** **6.2 Verify Post-Lockdown**

1. Classic cluster → Run test query → Should work ✅
2. SQL Warehouse → Run test query → Should work ✅
3. Public access (e.g., Storage Explorer) → Should fail ❌

---

***REMOVED******REMOVED*** 7. Troubleshooting

***REMOVED******REMOVED******REMOVED*** **Issue: SQL Warehouse Fails to Start**

**Symptoms**:
```
Error: Unable to connect to metastore
Error: Network connectivity issue
```

**Checks**:

1. **Verify NCC Binding**:
   ```bash
   terraform output ncc_id
   ***REMOVED*** Should NOT be null
   ```

2. **Check PE Approval Status**:
   - Azure Portal → Storage Accounts → Networking
   - All PE connections should be "Approved"

3. **Check Storage Firewall**:
   - If using Firewall option (not Private Link)
   - Verify serverless subnets are added

***REMOVED******REMOVED******REMOVED*** **Issue: Private Endpoint Shows "Pending"**

**Cause**: Manual approval required (cross-account connection)

**Solution**: Follow [Section 3.2](***REMOVED***32-approve-private-endpoint-connections)

**Note**: Terraform CANNOT auto-approve these (by Azure design)

***REMOVED******REMOVED******REMOVED*** **Issue: Query Succeeds But No Data**

**Symptoms**: SQL Warehouse runs but returns 0 rows for tables you know have data

**Checks**:

1. **Catalog/Schema Permissions**:
   ```sql
   SHOW GRANTS ON CATALOG <your_catalog>;
   SHOW GRANTS ON SCHEMA <your_schema>;
   ```

2. **External Location Access**:
   - Verify Access Connector has "Storage Blob Data Contributor" on UC storage

***REMOVED******REMOVED******REMOVED*** **Issue: "This request is not authorized"**

**Cause**: Storage firewall blocking access OR Private Endpoint not approved

**Solution**:

**If Classic Works, Serverless Doesn't**:
- NCC Private Endpoints not approved
- Go to Section 3.2

**If Neither Works**:
- VNet Private Endpoints issue
- Check Private Endpoints in Azure Portal
- Verify DNS resolution

***REMOVED******REMOVED******REMOVED*** **Issue: Serverless Option Not Available**

**Cause**: Workspace tier or region limitation

**Checks**:

1. **Workspace SKU**: Must be Premium
   ```bash
   terraform output workspace_sku
   ***REMOVED*** Should be "premium"
   ```

2. **Region Support**: Not all Azure regions support serverless
   - Check: https://learn.microsoft.com/en-us/azure/databricks/resources/supported-regions

---

***REMOVED******REMOVED*** 8. Cost Implications

***REMOVED******REMOVED******REMOVED*** **Serverless Pricing**

| Component | Cost | Notes |
|-----------|------|-------|
| **SQL Warehouse** | $0.22/DBU | Consumption-based |
| **Serverless Notebooks** | $0.07/DBU | Consumption-based |
| **Private Endpoints** | $0.01/hour each | ~$7.50/month per PE |
| **Data Transfer** | $0 | Within Azure region |

**Example**:
- 18 Private Endpoints (serverless): ~$135/month
- 10 hours SQL Warehouse (X-Small): ~$5/month
- **Total Incremental**: ~$140/month

**Recommendation**: Enable serverless only if you need it (classic clusters are more cost-effective for batch workloads)

---

***REMOVED******REMOVED*** 9. Quick Command Reference

***REMOVED******REMOVED******REMOVED*** **Check NCC Status**
```bash
terraform output ncc_id
terraform output ncc_name
```

***REMOVED******REMOVED******REMOVED*** **Get Storage Account Names**
```bash
terraform output metastore_storage_account_name
terraform output external_location_storage_account_name
```

***REMOVED******REMOVED******REMOVED*** **Check Workspace Config**
```bash
terraform output workspace_url
terraform output deployment_summary
```

***REMOVED******REMOVED******REMOVED*** **Test Connectivity** (from cluster notebook)
```python
***REMOVED*** Test Unity Catalog
spark.sql("SHOW CATALOGS").show()

***REMOVED*** Test external location
dbutils.fs.ls("abfss://<container>@<storage>.dfs.core.windows.net/")
```

---

***REMOVED******REMOVED*** 10. References

**Azure Official Documentation**:
- [Serverless Private Link](https://learn.microsoft.com/en-us/azure/databricks/security/network/serverless-network-security/serverless-private-link)
- [Serverless Firewall](https://learn.microsoft.com/en-us/azure/databricks/security/network/serverless-network-security/serverless-firewall)
- [Network Connectivity Configuration](https://learn.microsoft.com/en-us/azure/databricks/administration-guide/cloud-configurations/azure/ncc)

**Related Docs**:
- [01-ARCHITECTURE.md](01-ARCHITECTURE.md) - System design
- [README.md](README.md) - Documentation index

---

**Setup Type**: Optional (Classic clusters work without this)  
**Complexity**: Medium (requires Azure Portal steps)  
**Time**: 15-30 minutes (includes approval wait)  
**Prerequisites**: NCC attached, Classic clusters verified  

**Last Updated**: 2026-01-12
