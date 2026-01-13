***REMOVED*** BYOR (Bring Your Own Resources) Deployment

**Create Databricks-ready infrastructure** that can be reused across multiple workspace deployments.

---

***REMOVED******REMOVED*** 🎯 Purpose

The BYOR pattern creates pre-configured networking and security infrastructure that meets all Databricks requirements. This is ideal for enterprise teams that separate infrastructure provisioning (network team) from workspace deployment (platform team).

***REMOVED******REMOVED******REMOVED*** Use Cases

✅ **Separation of Concerns**: Network team manages infrastructure, platform team deploys workspaces  
✅ **Infrastructure Reuse**: Deploy multiple workspaces using the same network  
✅ **Pre-validated Setup**: All Databricks requirements configured correctly  
✅ **CMK Centralization**: Shared Key Vault across workspaces (optional)

---

***REMOVED******REMOVED*** 📦 What Gets Created

***REMOVED******REMOVED******REMOVED*** Always Created

- ✅ **VNet** with user-specified CIDR
- ✅ **Public/Host Subnet** with Databricks delegation
- ✅ **Private/Container Subnet** with Databricks delegation
- ✅ **NSG** with Databricks-required rules (service tags)
- ✅ **Service Endpoints** (Storage, KeyVault, EventHub)

***REMOVED******REMOVED******REMOVED*** Optional (Flag-Controlled)

- ⚙️ **NAT Gateway** (for Non-PL pattern) - `enable_nat_gateway = true`
- ⚙️ **Private Link Subnet** (for Full-Private pattern) - `create_privatelink_subnet = true`
- ⚙️ **Key Vault + CMK** (for encryption) - `create_key_vault = true`

---

***REMOVED******REMOVED*** 🚀 Quick Start

***REMOVED******REMOVED******REMOVED*** 1. Configure

```bash
cd deployments/byor
cp terraform.tfvars.example terraform.tfvars
vim terraform.tfvars
```

**Minimum Required Configuration**:
```hcl
workspace_prefix    = "<your-prefix>"      ***REMOVED*** e.g., "proddb", "devdb"
location            = "<azure-region>"      ***REMOVED*** e.g., "eastus2", "westus"
resource_group_name = "<rg-name>"          ***REMOVED*** e.g., "rg-databricks-byor-eastus2"

vnet_address_space           = ["<cidr>"]           ***REMOVED*** e.g., ["10.100.0.0/16"]
public_subnet_address_prefix  = "<public-cidr>"     ***REMOVED*** e.g., "10.100.1.0/26"
private_subnet_address_prefix = "<private-cidr>"    ***REMOVED*** e.g., "10.100.2.0/26"

enable_nat_gateway = true  ***REMOVED*** For Non-PL workspaces

tag_owner     = "<owner-email>"        ***REMOVED*** e.g., "platform-team@company.com"
tag_keepuntil = "<expiration-date>"    ***REMOVED*** e.g., "12/31/2026"
```

***REMOVED******REMOVED******REMOVED*** 2. Deploy

```bash
terraform init
terraform plan
terraform apply
```

***REMOVED******REMOVED******REMOVED*** 3. Get Copy-Paste Configuration

After successful deployment, get the configuration to use in workspace deployments:

```bash
***REMOVED*** View the output in terminal
terraform output copy_paste_config

***REMOVED*** Or save to file for easy copy-paste
terraform output -raw copy_paste_config > byor-config.txt
cat byor-config.txt
```

This outputs a ready-to-use configuration block like:

```hcl
***REMOVED*** ==============================================
***REMOVED*** BYOR Configuration (from BYOR deployment)
***REMOVED*** Copy-paste this section into deployments/non-pl/terraform.tfvars
***REMOVED*** or deployments/full-private/terraform.tfvars
***REMOVED*** ==============================================

***REMOVED*** Master Control - Use BYOR infrastructure
use_byor_infrastructure = true

***REMOVED*** Core Configuration - MUST match BYOR deployment
location            = "<azure-region>"
resource_group_name = "<rg-name>"

***REMOVED*** Network Configuration (from BYOR)
existing_vnet_name            = "<workspace-prefix>-vnet-<suffix>"
existing_resource_group_name  = "<rg-name>"
existing_public_subnet_name   = "<workspace-prefix>-public-subnet-<suffix>"
existing_private_subnet_name  = "<workspace-prefix>-private-subnet-<suffix>"
existing_nsg_name             = "<workspace-prefix>-nsg-<suffix>"

***REMOVED*** NSG Association IDs (required for workspace deployment)
existing_public_subnet_nsg_association_id  = "/subscriptions/<sub-id>/resourceGroups/<rg-name>/providers/Microsoft.Network/virtualNetworks/<vnet-name>/subnets/<public-subnet-name>"
existing_private_subnet_nsg_association_id = "/subscriptions/<sub-id>/resourceGroups/<rg-name>/providers/Microsoft.Network/virtualNetworks/<vnet-name>/subnets/<private-subnet-name>"

***REMOVED*** ==============================================
***REMOVED*** CMK Configuration (from BYOR deployment)
***REMOVED*** ==============================================

enable_cmk_managed_services = true
enable_cmk_managed_disks    = true
enable_cmk_dbfs_root        = true

***REMOVED*** Key Vault from BYOR
existing_key_vault_id = "/subscriptions/<sub-id>/resourceGroups/<rg-name>/providers/Microsoft.KeyVault/vaults/<kv-name>"
existing_key_id       = "https://<kv-name>.vault.azure.net/keys/databricks-cmk-<suffix>/<version>"
```

***REMOVED******REMOVED******REMOVED*** 4. Use in Workspace Deployment

**Option A: Direct Copy-Paste**

```bash
***REMOVED*** For Non-PL workspace
cd ../non-pl
vim terraform.tfvars
***REMOVED*** 1. Set: use_byor_infrastructure = true
***REMOVED*** 2. Paste the entire BYOR config section from above
terraform apply

***REMOVED*** OR for Full-Private workspace
cd ../full-private
vim terraform.tfvars
***REMOVED*** 1. Set: use_byor_infrastructure = true
***REMOVED*** 2. Paste the entire BYOR config section from above
terraform apply
```

**Option B: Using Saved File**

```bash
***REMOVED*** Save BYOR output
cd deployments/byor
terraform output -raw copy_paste_config > ../byor-config.txt

***REMOVED*** Apply to Non-PL workspace
cd ../non-pl
***REMOVED*** Open terraform.tfvars and paste contents from ../byor-config.txt
terraform apply

***REMOVED*** Apply to Full-Private workspace (reuse same config)
cd ../full-private
***REMOVED*** Open terraform.tfvars and paste contents from ../byor-config.txt
terraform apply
```

---

***REMOVED******REMOVED*** 📋 Configuration Options

***REMOVED******REMOVED******REMOVED*** For Non-PL Workspaces

```hcl
enable_nat_gateway        = true   ***REMOVED*** Required for internet egress
create_privatelink_subnet = false  ***REMOVED*** Not needed
create_key_vault          = false  ***REMOVED*** Optional
```

***REMOVED******REMOVED******REMOVED*** For Full-Private Workspaces

```hcl
enable_nat_gateway        = false  ***REMOVED*** No internet egress (air-gapped)
create_privatelink_subnet = true   ***REMOVED*** Required for Private Link
privatelink_subnet_address_prefix = "10.100.3.0/26"
create_key_vault          = false  ***REMOVED*** Optional
```

***REMOVED******REMOVED******REMOVED*** With Customer-Managed Keys

```hcl
create_key_vault = true
cmk_key_type     = "RSA"    ***REMOVED*** or "RSA-HSM"
cmk_key_size     = 2048     ***REMOVED*** or 3072, 4096
```

---

***REMOVED******REMOVED*** ✅ What's Pre-Configured

***REMOVED******REMOVED******REMOVED*** Subnet Delegation

All subnets automatically include:
```hcl
delegation {
  name = "Microsoft.Databricks/workspaces"
  actions = [
    "Microsoft.Network/virtualNetworks/subnets/join/action",
    "Microsoft.Network/virtualNetworks/subnets/prepareNetworkPolicies/action",
    "Microsoft.Network/virtualNetworks/subnets/unprepareNetworkPolicies/action"
  ]
}
```

***REMOVED******REMOVED******REMOVED*** Service Endpoints

All Databricks subnets include:
- ✅ `Microsoft.Storage`
- ✅ `Microsoft.KeyVault`
- ✅ `Microsoft.EventHub`

***REMOVED******REMOVED******REMOVED*** NSG Rules

Pre-configured with Databricks-required rules:
- ✅ **Outbound**: `AzureDatabricks` (443) - Control plane
- ✅ **Outbound**: `Storage` (443) - DBFS and artifacts
- ✅ **Outbound**: `EventHub` (443) - Logs and metrics
- ✅ **Inbound**: `VirtualNetwork` (all) - Worker communication

---

***REMOVED******REMOVED*** 🔍 Validation

BYOR automatically validates:
- ✅ Subnet CIDR sizes (minimum /26)
- ✅ workspace_prefix format (lowercase, max 12 chars)
- ✅ CMK key type and size (if enabled)

---

***REMOVED******REMOVED*** 📤 Outputs

***REMOVED******REMOVED******REMOVED*** Copy-Paste Ready

```bash
terraform output copy_paste_config
```

Provides a complete configuration block ready to paste into workspace deployments.

***REMOVED******REMOVED******REMOVED*** Individual Values

```bash
terraform output vnet_name
terraform output public_subnet_id
terraform output nat_gateway_public_ip
terraform output cmk_key_id
```

All outputs available programmatically for automation.

---

***REMOVED******REMOVED*** 🔄 Reusing Infrastructure

The same BYOR infrastructure can be used for **multiple workspaces**:

```bash
***REMOVED*** Deploy infrastructure once
cd deployments/byor
terraform apply

***REMOVED*** Get configuration
terraform output copy_paste_config > byor-config.txt

***REMOVED*** Deploy multiple workspaces using same network
cd ../non-pl
***REMOVED*** Paste config, set workspace_prefix = "workspace1"
terraform apply

cd ../non-pl-2
***REMOVED*** Paste same config, set workspace_prefix = "workspace2"
terraform apply
```

---

***REMOVED******REMOVED*** 🛠️ Advanced: CMK for Multiple Workspaces

When using CMK from BYOR across multiple workspaces:

1. **BYOR** creates Key Vault + CMK key
2. **Workspace 1** uses the CMK (adds access policies)
3. **Workspace 2** uses the same CMK (adds its own access policies)
4. **Workspace 3** uses the same CMK (adds its own access policies)

Each workspace's DBFS storage identity automatically gets access to the shared Key Vault.

---

***REMOVED******REMOVED*** 📚 Examples

See `terraform.tfvars.example` for complete examples:
- Example 1: Non-PL Infrastructure
- Example 2: Full-Private Infrastructure
- Example 3: Non-PL with CMK
- Example 4: Full-Private with CMK
- Example 5: Using Existing Resource Group

---

***REMOVED******REMOVED*** 🔄 Using BYOR with Workspace Deployments

***REMOVED******REMOVED******REMOVED*** Step-by-Step Workflow

**1. Deploy BYOR Infrastructure:**
```bash
cd deployments/byor
terraform apply

***REMOVED*** Get the copy-paste configuration
terraform output -raw copy_paste_config > ../byor-config.txt
***REMOVED*** or simply view it:
terraform output copy_paste_config
```

**2. Deploy Non-PL Workspace:**
```bash
cd ../non-pl
***REMOVED*** Edit terraform.tfvars:
***REMOVED***   - Set: use_byor_infrastructure = true
***REMOVED***   - Paste the BYOR output from ../byor-config.txt
terraform apply
```

**3. Deploy Full-Private Workspace (Same Network):**
```bash
cd ../full-private
***REMOVED*** Edit terraform.tfvars:
***REMOVED***   - Set: use_byor_infrastructure = true
***REMOVED***   - Paste the same BYOR output from ../byor-config.txt
terraform apply
```

***REMOVED******REMOVED******REMOVED*** What Happens

✅ **BYOR creates**: VNet, Subnets, NSG, NAT Gateway, Key Vault  
✅ **Non-PL workspace creates**: Workspace, Unity Catalog, NCC, SEP  
✅ **Full-Private workspace creates**: Workspace, Unity Catalog, Private Endpoints, NCC  

Both workspaces share the same network and Key Vault! 🎉

---

***REMOVED******REMOVED*** 🔗 Related Documentation

- [Non-PL Pattern](../../docs/patterns/01-NON-PL.md)
- [Full-Private Pattern](../../docs/patterns/02-FULL-PRIVATE.md)
- [Networking Module](../../docs/modules/01-NETWORKING.md)
- [CMK Module](../../docs/modules/05-CMK.md)

---

***REMOVED******REMOVED*** 💡 Best Practices

✅ **DO**:
- Use BYOR for production environments with multiple workspaces
- Tag resources appropriately for cost tracking
- Use /24 subnets for production (more IPs than minimum /26)
- Create CMK in BYOR if multiple workspaces need same encryption key
- Document the BYOR output for your team

❌ **DON'T**:
- Use BYOR for single workspace deployments (use Non-PL/Full-Private directly)
- Change network resources after workspace deployment
- Delete BYOR resources while workspaces are still using them
- Mix NAT Gateway and Private Link patterns in same network

---

**Ready to create your infrastructure?** Start with `terraform.tfvars.example`! 🚀
