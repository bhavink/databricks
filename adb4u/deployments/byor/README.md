# BYOR (Bring Your Own Resources) Deployment

**Create Databricks-ready infrastructure** that can be reused across multiple workspace deployments.

---

## 🎯 Purpose

The BYOR pattern creates pre-configured networking and security infrastructure that meets all Databricks requirements. This is ideal for enterprise teams that separate infrastructure provisioning (network team) from workspace deployment (platform team).

### Use Cases

✅ **Separation of Concerns**: Network team manages infrastructure, platform team deploys workspaces
✅ **Infrastructure Reuse**: Deploy multiple workspaces using the same network
✅ **Pre-validated Setup**: All Databricks requirements configured correctly
✅ **CMK Centralization**: Shared Key Vault across workspaces (optional)

---

## 📦 What Gets Created

### Always Created

- ✅ **VNet** with user-specified CIDR
- ✅ **Public/Host Subnet** with Databricks delegation
- ✅ **Private/Container Subnet** with Databricks delegation
- ✅ **NSG** with Databricks-required rules (service tags)
- ✅ **Service Endpoints** (Storage, KeyVault, EventHub)

### Optional (Flag-Controlled)

- ⚙️ **NAT Gateway** (for Non-PL pattern) - `enable_nat_gateway = true`
- ⚙️ **Private Link Subnet** (for Full-Private pattern) - `create_privatelink_subnet = true`
- ⚙️ **Key Vault + CMK** (for encryption) - `create_key_vault = true`

---

## 🚀 Quick Start

### 1. Configure

```bash
cd deployments/byor
cp terraform.tfvars.example terraform.tfvars
vim terraform.tfvars
```

**Minimum Required Configuration**:
```hcl
workspace_prefix    = "<your-prefix>"      # e.g., "proddb", "devdb"
location            = "<azure-region>"      # e.g., "eastus2", "westus"
resource_group_name = "<rg-name>"          # e.g., "rg-databricks-byor-eastus2"

vnet_address_space           = ["<cidr>"]           # e.g., ["10.100.0.0/16"]
public_subnet_address_prefix  = "<public-cidr>"     # e.g., "10.100.1.0/26"
private_subnet_address_prefix = "<private-cidr>"    # e.g., "10.100.2.0/26"

enable_nat_gateway = true  # For Non-PL workspaces

tag_owner     = "<owner-email>"        # e.g., "platform-team@company.com"
tag_keepuntil = "<expiration-date>"    # e.g., "12/31/2026"
```

### 2. Deploy

```bash
terraform init
terraform plan
terraform apply
```

### 3. Get Copy-Paste Configuration

After successful deployment, get the configuration to use in workspace deployments:

```bash
# View the output in terminal
terraform output copy_paste_config

# Or save to file for easy copy-paste
terraform output -raw copy_paste_config > byor-config.txt
cat byor-config.txt
```

This outputs a ready-to-use configuration block like:

```hcl
# ==============================================
# BYOR Configuration (from BYOR deployment)
# Copy-paste this section into deployments/non-pl/terraform.tfvars
# or deployments/full-private/terraform.tfvars
# ==============================================

# Master Control - Use BYOR infrastructure
use_byor_infrastructure = true

# Core Configuration - MUST match BYOR deployment
location            = "<azure-region>"
resource_group_name = "<rg-name>"

# Network Configuration (from BYOR)
existing_vnet_name            = "<workspace-prefix>-vnet-<suffix>"
existing_resource_group_name  = "<rg-name>"
existing_public_subnet_name   = "<workspace-prefix>-public-subnet-<suffix>"
existing_private_subnet_name  = "<workspace-prefix>-private-subnet-<suffix>"
existing_nsg_name             = "<workspace-prefix>-nsg-<suffix>"

# NSG Association IDs (required for workspace deployment)
existing_public_subnet_nsg_association_id  = "/subscriptions/<sub-id>/resourceGroups/<rg-name>/providers/Microsoft.Network/virtualNetworks/<vnet-name>/subnets/<public-subnet-name>"
existing_private_subnet_nsg_association_id = "/subscriptions/<sub-id>/resourceGroups/<rg-name>/providers/Microsoft.Network/virtualNetworks/<vnet-name>/subnets/<private-subnet-name>"

# ==============================================
# CMK Configuration (from BYOR deployment)
# ==============================================

enable_cmk_managed_services = true
enable_cmk_managed_disks    = true
enable_cmk_dbfs_root        = true

# Key Vault from BYOR
existing_key_vault_id = "/subscriptions/<sub-id>/resourceGroups/<rg-name>/providers/Microsoft.KeyVault/vaults/<kv-name>"
existing_key_id       = "https://<kv-name>.vault.azure.net/keys/databricks-cmk-<suffix>/<version>"
```

### 4. Use in Workspace Deployment

**Option A: Direct Copy-Paste**

```bash
# For Non-PL workspace
cd ../non-pl
vim terraform.tfvars
# 1. Set: use_byor_infrastructure = true
# 2. Paste the entire BYOR config section from above
terraform apply

# OR for Full-Private workspace
cd ../full-private
vim terraform.tfvars
# 1. Set: use_byor_infrastructure = true
# 2. Paste the entire BYOR config section from above
terraform apply
```

**Option B: Using Saved File**

```bash
# Save BYOR output
cd deployments/byor
terraform output -raw copy_paste_config > ../byor-config.txt

# Apply to Non-PL workspace
cd ../non-pl
# Open terraform.tfvars and paste contents from ../byor-config.txt
terraform apply

# Apply to Full-Private workspace (reuse same config)
cd ../full-private
# Open terraform.tfvars and paste contents from ../byor-config.txt
terraform apply
```

---

## 📋 Configuration Options

### For Non-PL Workspaces

```hcl
enable_nat_gateway        = true   # Required for internet egress
create_privatelink_subnet = false  # Not needed
create_key_vault          = false  # Optional
```

### For Full-Private Workspaces

```hcl
enable_nat_gateway        = false  # No internet egress (air-gapped)
create_privatelink_subnet = true   # Required for Private Link
privatelink_subnet_address_prefix = "10.100.3.0/26"
create_key_vault          = false  # Optional
```

### With Customer-Managed Keys

```hcl
create_key_vault = true
cmk_key_type     = "RSA"    # or "RSA-HSM"
cmk_key_size     = 2048     # or 3072, 4096
```

---

## ✅ What's Pre-Configured

### Subnet Delegation

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

### Service Endpoints

All Databricks subnets include:
- ✅ `Microsoft.Storage`
- ✅ `Microsoft.KeyVault`
- ✅ `Microsoft.EventHub`

### NSG Rules

Pre-configured with Databricks-required rules:
- ✅ **Outbound**: `AzureDatabricks` (443) - Control plane
- ✅ **Outbound**: `Storage` (443) - DBFS and artifacts
- ✅ **Outbound**: `EventHub` (443) - Logs and metrics
- ✅ **Inbound**: `VirtualNetwork` (all) - Worker communication

---

## 🔍 Validation

BYOR automatically validates:
- ✅ Subnet CIDR sizes (minimum /26)
- ✅ workspace_prefix format (lowercase, max 12 chars)
- ✅ CMK key type and size (if enabled)

---

## 📤 Outputs

### Copy-Paste Ready

```bash
terraform output copy_paste_config
```

Provides a complete configuration block ready to paste into workspace deployments.

### Individual Values

```bash
terraform output vnet_name
terraform output public_subnet_id
terraform output nat_gateway_public_ip
terraform output cmk_key_id
```

All outputs available programmatically for automation.

---

## 🔄 Reusing Infrastructure

The same BYOR infrastructure can be used for **multiple workspaces**:

```bash
# Deploy infrastructure once
cd deployments/byor
terraform apply

# Get configuration
terraform output copy_paste_config > byor-config.txt

# Deploy multiple workspaces using same network
cd ../non-pl
# Paste config, set workspace_prefix = "workspace1"
terraform apply

cd ../non-pl-2
# Paste same config, set workspace_prefix = "workspace2"
terraform apply
```

---

## 🛠️ Advanced: CMK for Multiple Workspaces

When using CMK from BYOR across multiple workspaces:

1. **BYOR** creates Key Vault + CMK key
2. **Workspace 1** uses the CMK (adds access policies)
3. **Workspace 2** uses the same CMK (adds its own access policies)
4. **Workspace 3** uses the same CMK (adds its own access policies)

Each workspace's DBFS storage identity automatically gets access to the shared Key Vault.

---

## 📚 Examples

See `terraform.tfvars.example` for complete examples:
- Example 1: Non-PL Infrastructure
- Example 2: Full-Private Infrastructure
- Example 3: Non-PL with CMK
- Example 4: Full-Private with CMK
- Example 5: Using Existing Resource Group

---

## 🔄 Using BYOR with Workspace Deployments

### Step-by-Step Workflow

**1. Deploy BYOR Infrastructure:**
```bash
cd deployments/byor
terraform apply

# Get the copy-paste configuration
terraform output -raw copy_paste_config > ../byor-config.txt
# or simply view it:
terraform output copy_paste_config
```

**2. Deploy Non-PL Workspace:**
```bash
cd ../non-pl
# Edit terraform.tfvars:
#   - Set: use_byor_infrastructure = true
#   - Paste the BYOR output from ../byor-config.txt
terraform apply
```

**3. Deploy Full-Private Workspace (Same Network):**
```bash
cd ../full-private
# Edit terraform.tfvars:
#   - Set: use_byor_infrastructure = true
#   - Paste the same BYOR output from ../byor-config.txt
terraform apply
```

### What Happens

✅ **BYOR creates**: VNet, Subnets, NSG, NAT Gateway, Key Vault
✅ **Non-PL workspace creates**: Workspace, Unity Catalog, NCC, SEP
✅ **Full-Private workspace creates**: Workspace, Unity Catalog, Private Endpoints, NCC

Both workspaces share the same network and Key Vault! 🎉

---

## 🔗 Related Documentation

- [Non-PL Pattern](../../docs/patterns/01-NON-PL.md)
- [Full-Private Pattern](../../docs/patterns/02-FULL-PRIVATE.md)
- [Networking Module](../../docs/modules/01-NETWORKING.md)
- [CMK Module](../../docs/modules/05-CMK.md)

---

## 💡 Best Practices

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
