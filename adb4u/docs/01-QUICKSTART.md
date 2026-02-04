# Quick Start Guide - Non-PL Deployment

Deploy your first Azure Databricks workspace using the Non-Private Link pattern.

## ⏱️ Estimated Time: 20 minutes

## ✅ Prerequisites Checklist

- [ ] Azure subscription with Contributor + User Access Administrator roles
- [ ] Terraform >= 1.5 installed (`terraform version`)
- [ ] Azure CLI installed and logged in (`az login`)
- [ ] Databricks Account ID from https://accounts.azuredatabricks.net

## 🚀 Deployment Steps

### Step 1: Set Environment Variables

```bash
# Set Databricks Account ID
export TF_VAR_databricks_account_id="<your-databricks-account-id>"

# Verify
echo $TF_VAR_databricks_account_id
```

### Step 2: Navigate to Deployment

```bash
cd /path/to/0-repo/databricks/adb4u/deployments/non-pl
```

### Step 3: Configure Deployment

```bash
# Copy example configuration
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
vim terraform.tfvars
```

**Required values in `terraform.tfvars`:**
```hcl
workspace_prefix        = "mydb"          # lowercase, max 12 chars
location                = "eastus2"        # Azure region
resource_group_name     = "rg-databricks-prod"
databricks_account_id   = "<from-step-1>"
```

### Step 4: Initialize Terraform

```bash
terraform init
```

**Expected output:**
```
Initializing modules...
- networking in ../../modules/networking
- workspace in ../../modules/workspace
- unity_catalog in ../../modules/unity-catalog

Terraform has been successfully initialized!
```

### Step 5: Validate Configuration

```bash
terraform validate
```

**Expected:** `Success! The configuration is valid.`

### Step 6: Review Plan

```bash
terraform plan -out=tfplan
```

**Review the plan carefully. You should see:**
- 1 Resource Group
- 1 VNet + 2 Subnets
- 1 NSG with SCC rules
- 1 NAT Gateway + Public IP
- 1 Databricks Workspace
- 2 Storage Accounts (metastore + external)
- 1 Access Connector
- Unity Catalog resources

### Step 7: Apply Configuration

```bash
terraform apply tfplan
```

**Duration:** ~15-20 minutes

### Step 8: Get Outputs

```bash
# View workspace URL
terraform output workspace_url

# View all outputs
terraform output

# Save metastore ID for future workspaces
terraform output metastore_id > metastore-id.txt
```

## ✅ Verification

### 1. Access Workspace

```bash
# Open workspace in browser
open $(terraform output -raw workspace_url)
```

### 2. Verify Network Configuration

In Azure Portal, check:
- Resource group exists
- VNet has 2 subnets with Databricks delegation
- NSG attached to both subnets
- NAT Gateway created

### 3. Test Compute

1. In Databricks workspace, create a cluster
2. Verify cluster has no public IPs (NPIP working)
3. Test package installation (validates NAT Gateway):
   ```python
   %pip install pandas
   ```

### 4. Test Unity Catalog

1. Navigate to Data → Unity Catalog
2. Verify metastore is attached
3. Create a catalog: `CREATE CATALOG test_catalog`
4. Check external location is available

## 🐛 Troubleshooting

### Issue: "databricks_account_id must be a valid UUID"
**Solution:** Verify format is `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` (no spaces)

### Issue: "Insufficient privileges"
**Solution:** Ensure you have Contributor + User Access Administrator roles

### Issue: "Subnet delegation not found" (BYOV only)
**Solution:** Add delegation manually:
```bash
az network vnet subnet update \
  --resource-group <rg> \
  --vnet-name <vnet> \
  --name <subnet> \
  --delegations Microsoft.Databricks/workspaces
```

### Issue: Cannot install packages
**Solution:** Verify NAT Gateway is created and associated with subnets

## 📊 What Was Created?

| Resource Type | Count | Purpose |
|---------------|-------|---------|
| Resource Group | 1 | Container for all resources |
| VNet | 1 | Network isolation |
| Subnets | 2 | Public + Private for Databricks |
| NSG | 1 | Network security rules |
| NAT Gateway | 1 | Stable outbound IP |
| Public IP | 1 | For NAT Gateway |
| Databricks Workspace | 1 | Main workspace |
| Storage Accounts | 2 | Metastore + External location |
| Access Connector | 1 | Unity Catalog managed identity |

**Monthly Cost:** ~$58 (infrastructure only, compute is additional)

## 🎯 Next Steps

1. **Configure Users & Groups**
   - Set up Azure AD SCIM provisioning
   - Assign workspace roles

2. **Create Compute Policies**
   - Define cluster policies
   - Set up cluster pools

3. **Set Up Unity Catalog**
   - Create catalogs and schemas
   - Configure external locations
   - Set up data access permissions

4. **Enable Monitoring**
   - Configure diagnostic logs
   - Set up Azure Monitor integration

5. **Deploy Additional Workspaces**
   - Reuse metastore for same region
   - Set `create_metastore = false`
   - Reference `existing_metastore_id`

## 🧹 Cleanup (Testing Only)

```bash
terraform destroy
```

**⚠️ Warning:** This will delete everything including Unity Catalog data!

## 📚 More Information

- **Authentication Options:** See `docs/02-AUTHENTICATION.md`
- **Architecture Details:** See [Non-PL Pattern](patterns/01-NON-PL.md)
- **Troubleshooting:** See `docs/04-TROUBLESHOOTING.md`
- **Module Details:** See `docs/modules/` folder

---

**Need Help?** Check the troubleshooting guide or raise an issue in the repository.
