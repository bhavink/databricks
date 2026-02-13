# Serverless Compute Setup Guide

> **Enable Serverless SQL Warehouses and Serverless Notebooks** with private connectivity to customer storage and Azure services.
>
> **Applies to**: Non-PL and Full-Private deployment patterns

---

## 📋 **Table of Contents**

1. [Overview](#1-overview)
2. [Prerequisites](#2-prerequisites)
3. [Serverless Connectivity Options](#3-serverless-connectivity-options)
4. [Option A: Service Endpoints (Recommended)](#4-option-a-service-endpoints-recommended)
5. [Option B: Private Link via NCC](#5-option-b-private-link-via-ncc)
6. [Testing Serverless](#6-testing-serverless)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Overview

### **What is Serverless Compute?**

Serverless compute runs in **Databricks-managed Azure VNet** (not your VNet like classic clusters).

| Aspect | Classic Clusters | Serverless Compute |
|--------|------------------|-------------------|
| **Where Runs** | Customer VNet | Databricks SaaS VNet |
| **Storage Access** | Direct (via Service Endpoints in VNet) | Via NCC configuration |
| **Approval** | N/A (runs in your VNet) | Varies by connectivity option |
| **Use Cases** | ETL, ML training, batch jobs | SQL Warehouses, ad-hoc queries |

### **Deployment Status**

After `terraform apply`, your workspace has:
- ✅ **NCC Attached**: Network Connectivity Configuration created and bound
- ✅ **Classic Clusters**: Work immediately with Service Endpoints
- ⏸️ **Serverless**: Requires additional configuration (this guide)

---

## 2. Prerequisites

**Before Starting**:
- ✅ Workspace deployed successfully
- ✅ Classic cluster tested and working
- ✅ Unity Catalog functional
- ✅ NCC attached (check `terraform output ncc_id`)

**What You'll Configure**:
- Serverless connectivity to Unity Catalog storage
- Serverless connectivity to external customer storage (optional)
- Serverless connectivity to other Azure services (optional)

---

## 3. Serverless Connectivity Options

### **Two Approaches**

#### **Option A: Service Endpoints (Recommended)**
- ✅ **Setup**: Simple configuration
- ✅ **Performance**: Good latency
- ⚠️ **Security**: Traffic stays on Azure backbone (not internet), but not isolated
- ✅ **Best For**: Most deployments

#### **Option B: Private Link via NCC**
- ✅ **Setup**: Manual approval required in Azure Portal
- ✅ **Performance**: Best latency
- ✅ **Security**: Fully isolated (no public network routing)
- ✅ **Best For**: Highly regulated environments, zero-trust networks

---

## 4. Option A: Service Endpoints (Recommended)

### **How It Works**

```
Serverless Compute → NCC → Service Endpoint → Storage Account
(Databricks VNet)    ↓     (Azure backbone)    (Your subscription)
                  Firewall Rules
```

**Traffic Flow**:
1. Serverless compute initiates connection
2. Databricks routes via Azure Service Endpoints
3. Storage firewall allows Databricks serverless subnets
4. Data returned via Azure backbone (never touches internet)

---

### **Step 1: Enable Serverless in Databricks UI**

1. **Navigate to Admin Console**:
   ```
   Workspace → Settings → Network → Serverless Compute
   ```

2. **Enable Serverless**:
   - Toggle "Enable Serverless SQL Warehouses" → **ON**
   - Toggle "Enable Serverless Notebooks" → **ON** (optional)

3. **Select NCC**:
   - Choose your NCC from dropdown (should auto-detect)
   - NCC Name: `<workspace-prefix>-ncc`

4. **Save Configuration**

---

### **Step 2: Configure Storage Firewall with Serverless Subnets**

Databricks serverless will access your storage from specific subnets. You need to allow these subnets in your storage firewall.

#### **Get Serverless Subnet IDs**

After enabling serverless, Databricks will display the serverless subnet IDs in the UI:

```
Workspace → Settings → Network → Serverless Compute → View Details
```

**Example Subnet IDs**:
```
/subscriptions/.../resourceGroups/databricks-rg-<workspace>/providers/Microsoft.Network/virtualNetworks/workers-vnet/subnets/serverless-public
/subscriptions/.../resourceGroups/databricks-rg-<workspace>/providers/Microsoft.Network/virtualNetworks/workers-vnet/subnets/serverless-private
```

#### **Update Storage Account Firewall**

**For UC Metastore Storage**:

```bash
# Get storage account name
UC_METASTORE_STORAGE=$(terraform output -raw external_storage_account_name)

# Add serverless subnets to firewall
az storage account network-rule add \
  --account-name $UC_METASTORE_STORAGE \
  --subnet "<SERVERLESS_PUBLIC_SUBNET_ID>" \
  --resource-group <rg-name>

az storage account network-rule add \
  --account-name $UC_METASTORE_STORAGE \
  --subnet "<SERVERLESS_PRIVATE_SUBNET_ID>" \
  --resource-group <rg-name>
```

**For External Customer Storage** (if applicable):
- Repeat the above commands for any customer storage accounts that serverless needs to access

---

### **Step 3: Test Serverless SQL Warehouse**

1. **Create SQL Warehouse**:
   ```
   Workspace → SQL Warehouses → Create SQL Warehouse
   ```
   - Name: `Serverless Test Warehouse`
   - Type: **Serverless**
   - Size: **X-Small**

2. **Run Test Query**:
   ```sql
   -- Test Unity Catalog access
   SHOW CATALOGS;

   -- Test external location access
   SELECT * FROM <catalog>.<schema>.<table> LIMIT 10;
   ```

3. **Expected Result**: ✅ Query returns data successfully

---

### **Step 4: (Optional) Lock Down Storage**

If you want to disable public access completely:

```bash
# Disable public network access (use with caution!)
az storage account update \
  --name $UC_METASTORE_STORAGE \
  --resource-group <rg-name> \
  --public-network-access Disabled
```

⚠️ **Warning**: This will break classic clusters unless you also add your VNet subnets to the firewall or use Private Endpoints.

**Recommended Approach**:
- Keep public access **enabled**
- Use firewall rules to allow only:
  - Your VNet subnets (for classic clusters)
  - Databricks serverless subnets
  - Your corporate network IP ranges

---

## 5. Option B: Private Link via NCC

### **How It Works**

```
Serverless Compute → NCC → Private Endpoint → Storage Account
(Databricks VNet)    ↓     (Private Link)      (Your subscription)
                  Manual Approval
```

**Key Difference**: Databricks creates Private Endpoint connections from **its managed VNet** to **your storage**, which requires **manual approval**.

---

### **Step 1: Enable Serverless with Private Link**

1. **Navigate to Admin Console**:
   ```
   Workspace → Settings → Network → Serverless Compute
   ```

2. **Enable Serverless**:
   - Toggle "Enable Serverless SQL Warehouses" → **ON**
   - Select **Private Link** connectivity option

3. **Select Storage Accounts**:
   - Select UC Metastore storage
   - Select any external customer storage

4. **Save Configuration**

**What Happens**:
- Databricks initiates Private Endpoint connections from its VNet to your storage
- Connections appear as "Pending" in Azure Portal
- **You must approve them** (next step)

---

### **Step 2: Approve Private Endpoint Connections**

#### **Via Azure Portal**

1. **Navigate to Storage Account**:
   ```
   Azure Portal → Storage Accounts → <uc-metastore-storage> → Networking
   ```

2. **Go to Private Endpoint Connections**:
   ```
   Networking → Private endpoint connections
   ```

3. **Approve Pending Connections**:
   - Look for connections from `databricks-*`
   - Status: **Pending**
   - Click each connection → **Approve**

4. **Repeat for All Storage Accounts**:
   - UC Metastore storage
   - UC External storage (if using)
   - Any customer storage accounts

**Approval Timeline**: ~2-5 minutes per storage account

---

#### **Via Azure CLI**

```bash
# List pending private endpoint connections
az storage account private-endpoint-connection list \
  --account-name <storage-account-name> \
  --resource-group <rg-name> \
  --query "[?properties.privateLinkServiceConnectionState.status=='Pending']"

# Approve connection
az storage account private-endpoint-connection approve \
  --account-name <storage-account-name> \
  --resource-group <rg-name> \
  --name <connection-name> \
  --description "Approved for Databricks serverless"
```

---

### **Step 3: Verify Connection Status**

**In Databricks UI**:
```
Workspace → Settings → Network → Serverless Compute → View Private Link Status
```

**Expected**: All connections show **"Connected"** or **"Approved"**

---

### **Step 4: Lock Down Storage (Optional but Recommended)**

Once Private Link is working:

```bash
# Disable public network access
az storage account update \
  --name <storage-account-name> \
  --resource-group <rg-name> \
  --public-network-access Disabled
```

⚠️ **Important**:
- Classic clusters will break unless they also use Private Endpoints
- Consider keeping public access enabled with firewall rules instead
- Or deploy Private Endpoints for classic clusters as well

---

### **Step 5: Test Serverless SQL Warehouse**

Same as Option A Step 3.

---

## 6. Testing Serverless

### **Test Checklist**

#### **SQL Warehouse Test**

```sql
-- 1. Test catalog access
SHOW CATALOGS;

-- 2. Test schema access
SHOW SCHEMAS IN <catalog>;

-- 3. Test table access
SELECT * FROM <catalog>.<schema>.<table> LIMIT 10;

-- 4. Test write operations
CREATE TABLE <catalog>.<schema>.test_table AS
SELECT 1 as id, 'test' as name;
```

#### **Serverless Notebook Test** (Optional)

```python
# Test Unity Catalog access
catalogs = spark.sql("SHOW CATALOGS").collect()
print(f"Found {len(catalogs)} catalogs")

# Test external location read
df = spark.read.table("<catalog>.<schema>.<table>")
display(df.limit(10))

# Test external location write
df.write.mode("overwrite").saveAsTable("<catalog>.<schema>.test_table")
```

---

## 7. Troubleshooting

### **Issue: SQL Warehouse Fails to Start**

**Symptoms**:
```
Error: Unable to connect to storage
Error: Network connectivity issue
```

**Check**:

1. **NCC Attached**:
   ```bash
   terraform output ncc_id
   # Should return: ncc-<id>
   ```

2. **Serverless Enabled**:
   - Databricks UI → Settings → Network → Serverless
   - Should show "Enabled"

3. **Storage Firewall** (Service Endpoints):
   - Verify serverless subnets added to storage firewall
   - Check: Azure Portal → Storage → Networking → Firewalls and virtual networks

4. **Private Link Status** (Private Link):
   - Verify all connections "Approved"
   - Check: Azure Portal → Storage → Networking → Private endpoint connections

---

### **Issue: Queries Work But Slow Performance**

**Possible Causes**:
- Service Endpoint routing inefficient
- Consider switching to Private Link for better latency
- Check if storage account is in same region as workspace

**Solution**:
- Verify storage account region matches workspace region
- Consider Private Link for production workloads

---

### **Issue: Cannot Write to External Location**

**Symptoms**:
```
Error: Access denied to path abfss://...
Error: Permission denied
```

**Check**:

1. **Access Connector Permissions**:
   ```bash
   # Verify Access Connector has "Storage Blob Data Contributor"
   az role assignment list \
     --assignee <access-connector-principal-id> \
     --scope <storage-account-id>
   ```

2. **Unity Catalog Credential**:
   ```sql
   -- Verify storage credential exists
   SHOW STORAGE CREDENTIALS;

   -- Verify external location exists
   SHOW EXTERNAL LOCATIONS;
   ```

3. **Catalog Permissions**:
   ```sql
   -- Grant permissions
   GRANT USE CATALOG ON CATALOG <catalog> TO <user>;
   GRANT CREATE SCHEMA ON CATALOG <catalog> TO <user>;
   ```

---

### **Issue: Private Endpoint Connection Stuck "Pending"**

**Possible Causes**:
- Manual approval not completed
- Azure RBAC permissions insufficient

**Solution**:

1. **Check Azure Portal**:
   - Storage Account → Networking → Private endpoint connections
   - Manually approve each pending connection

2. **Verify Permissions**:
   - User must have `Microsoft.Storage/storageAccounts/privateEndpointConnectionsApproval/action`
   - Or be Owner/Contributor on storage account

3. **Retry if Timeout**:
   - If connection times out (>10 minutes), recreate from Databricks UI

---

## 📚 **Additional Resources**

**Azure Documentation**:
- [Serverless Network Security](https://learn.microsoft.com/en-us/azure/databricks/security/network/serverless-network-security/serverless-firewall)
- [Serverless Private Link](https://learn.microsoft.com/en-us/azure/databricks/security/network/serverless-network-security/serverless-private-link)
- [Service Endpoints](https://learn.microsoft.com/en-us/azure/virtual-network/virtual-network-service-endpoints-overview)

**Databricks Documentation**:
- [Serverless Compute](https://learn.microsoft.com/en-us/azure/databricks/serverless-compute/)
- [SQL Warehouses](https://learn.microsoft.com/en-us/azure/databricks/sql/admin/sql-warehouses)
- [Network Connectivity Configuration](https://learn.microsoft.com/en-us/azure/databricks/security/network/serverless-network-security/)

---

**Applies to**: Non-PL and Full-Private patterns
**Status**: ✅ Serverless Ready (requires post-deployment setup)
