***REMOVED*** Full Private Azure Databricks - Documentation Index

> **Start Here**: Complete visual guide for deploying Full Private Azure Databricks workspaces.

***REMOVED******REMOVED*** 📚 Documentation Structure

```
Visual-First Documentation:
├── 01-ARCHITECTURE.md        → Architecture & deployment flow 📐
├── 04-SERVERLESS-SETUP.md    → Enable serverless compute 🚀
├── 06-TROUBLESHOOTING.md     → Common issues & solutions 🔧
└── README.md                  → This file (navigation) 📖

Coming Soon (Lower Priority):
├── 00-PREREQUISITES.md       → System setup & credentials ⚙️
├── 02-PRIVATE-LINK-SECURITY.md → Private Link & NCC 🔐
├── 03-NETWORK-TRAFFIC.md     → Traffic flows & diagrams 🛡️
└── 05-QUICK-START.md         → 5-minute deployment guide ⚡
```

---

***REMOVED******REMOVED*** 🚀 Quick Navigation

**First Time User?**
1. Review [01-ARCHITECTURE.md](01-ARCHITECTURE.md) - Understand the design
2. Configure `terraform.tfvars` in `deployments/full-private/`
3. Run `terraform apply`
4. Create a classic cluster and verify functionality
5. (Optional) Follow [04-SERVERLESS-SETUP.md](04-SERVERLESS-SETUP.md) to enable serverless

**Want to Enable Serverless?**
- [04-SERVERLESS-SETUP.md](04-SERVERLESS-SETUP.md) - Complete guide with Azure Portal steps

**Having Problems?**
- [06-TROUBLESHOOTING.md](06-TROUBLESHOOTING.md) - Error messages, solutions, and debugging
- Check deployment outputs for next steps
- Review `checkpoint/FULL-PRIVATE-IMPLEMENTATION-COMPLETE.md`

---

***REMOVED******REMOVED*** 📖 Document Summaries

***REMOVED******REMOVED******REMOVED*** [01-ARCHITECTURE.md](01-ARCHITECTURE.md)
**Architecture Overview**: Complete system design with modular visual diagrams
- High-level architecture (VNet, Private Endpoints, NCC)
- Module dependency flow (6 Terraform modules)
- Network layout (3 subnet tiers: public, private, privatelink)
- Private Endpoint architecture (Databricks + Storage)
- Deployment sequence diagrams
- Resource breakdown (~35-40 resources)
- Classic vs. Serverless compute paths

***REMOVED******REMOVED******REMOVED*** [04-SERVERLESS-SETUP.md](04-SERVERLESS-SETUP.md)
**Serverless Enablement**: Step-by-step guide to enable serverless compute with private connectivity
- Prerequisites (NCC attached, classic clusters working)
- Option A: Private Link setup (recommended for air-gapped)
- Option B: Firewall setup (hybrid connectivity)
- Azure Portal approval workflow
- Storage lockdown procedures
- Testing serverless (SQL Warehouses, Serverless Notebooks)
- Troubleshooting serverless connectivity

***REMOVED******REMOVED******REMOVED*** [06-TROUBLESHOOTING.md](06-TROUBLESHOOTING.md)
**Troubleshooting Guide**: Common errors, solutions, and debugging steps
- Deployment issues (NSG conflicts, NCC timeouts)
- Unity Catalog issues (metastore deletion, storage access)
- Network connectivity (Private Endpoints, DNS, access)
- Destroy issues (UC metastore, NCC, storage accounts)
- Serverless issues (SQL Warehouse, permissions, Private Link)
- Quick commands (state management, validation, debugging)
- Error dictionary (common error messages + solutions)

---

***REMOVED******REMOVED*** 🏗️ Deployment Pattern Overview

***REMOVED******REMOVED******REMOVED*** **What Gets Deployed**

**Control Plane Access**: Private Link  
**Data Plane**: NPIP (no public IPs) + VNet injection  
**Egress**: None (air-gapped) or controlled via firewall  
**Storage**: Private Endpoints  
**Unity Catalog**: Enabled with private storage  
**NCC**: Attached (serverless-ready)

***REMOVED******REMOVED******REMOVED*** **Resource Count**: ~35-40 Resources

```
📦 Core Infrastructure:
├── 1 Resource Group
├── 1 VNet (3 subnets)
├── 1 NSG (Databricks-managed rules)
├── 10 Private Endpoints
├── 3 Private DNS Zones
└── 1 NCC Configuration + Binding

🏢 Databricks & Data:
├── 1 Workspace (Private Link enabled)
├── 3 Storage Accounts (DBFS + UC Metastore + UC External)
├── 1 Access Connector (Managed Identity)
└── 1 Unity Catalog Metastore

⏱️ Deployment Time: 15-20 minutes
💰 Estimated Cost: ~$120-150/month (without compute)
```

---

***REMOVED******REMOVED*** 🎯 Deployment Workflow

***REMOVED******REMOVED******REMOVED*** **Phase 1: Initial Deployment** ✅
```bash
cd deployments/full-private
terraform init
terraform plan
terraform apply
```

**Result**:
- Workspace accessible (public access enabled by default)
- Classic clusters work immediately
- Unity Catalog functional
- NCC attached (serverless-ready)

**Validate**:
1. Visit workspace URL (check deployment outputs)
2. Create a classic cluster
3. Run a simple notebook
4. Query Unity Catalog

***REMOVED******REMOVED******REMOVED*** **Phase 2: Enable Serverless** ⏸️ (Optional)
Follow [04-SERVERLESS-SETUP.md](04-SERVERLESS-SETUP.md)

**Steps**:
1. Enable serverless storage connectivity (Private Link OR Firewall)
2. Approve Private Endpoint connections in Azure Portal
3. Lock down storage (disable public access)
4. Test SQL Warehouse or Serverless Notebook

***REMOVED******REMOVED******REMOVED*** **Phase 3: Lock Down (Optional)** 🔒
```hcl
***REMOVED*** terraform.tfvars
enable_public_network_access = false  ***REMOVED*** Air-gapped
enable_ip_access_lists = true          ***REMOVED*** OR use IP restrictions
```

---

***REMOVED******REMOVED*** 🔐 Security Posture

***REMOVED******REMOVED******REMOVED*** **Network Isolation**
- ✅ **Private Link** for Databricks Control Plane
- ✅ **NPIP/SCC** (no public IPs on cluster nodes)
- ✅ **Private Endpoints** for all storage (classic clusters)
- ✅ **VNet Injection** (clusters run in customer VNet)
- ⏸️ **No NAT Gateway** (air-gapped, no internet egress)

***REMOVED******REMOVED******REMOVED*** **Access Control**
- ✅ **Public access** (default, for deployment convenience)
- ✅ **IP Access Lists** (recommended for security)
- ⏸️ **Air-gapped mode** (optional, requires VPN/Bastion)

***REMOVED******REMOVED******REMOVED*** **Data Protection**
- ✅ **Unity Catalog** (data governance)
- ✅ **Private storage** (ADLS Gen2 with Private Endpoints)
- ✅ **Managed Identity** (Access Connector for UC)
- ⏸️ **CMK** (optional customer-managed keys)

---

***REMOVED******REMOVED*** 🆚 Classic vs. Serverless Compute

| Feature | Classic Clusters | Serverless Compute |
|---------|-----------------|-------------------|
| **Deployment** | ✅ Works immediately | ⏸️ Requires setup |
| **Storage Access** | Via VNet Private Endpoints | Via NCC Private Endpoints |
| **Approval Required** | ❌ No (auto-approved) | ✅ Yes (Azure Portal) |
| **Use Cases** | ETL, ML training, batch jobs | SQL Warehouses, ad-hoc queries |
| **Control** | Full (VM management) | Limited (serverless) |
| **Cost** | Per-VM pricing | Consumption-based |

**Recommendation**: Deploy with classic clusters first, enable serverless when needed.

---

***REMOVED******REMOVED*** 💡 Key Design Decisions

***REMOVED******REMOVED******REMOVED*** **1. NCC Attached, No PE Rules in Terraform**

**Why**: NCC Private Endpoint connections require manual approval in Azure Portal (cross-account). Terraform would timeout.

**What's Created**:
- ✅ NCC Configuration
- ✅ NCC Binding to workspace
- ❌ NO PE rules (customer creates manually)

**Impact**:
- Classic clusters work immediately (use VNet PE)
- Serverless requires manual setup (see docs/04-SERVERLESS-SETUP.md)

***REMOVED******REMOVED******REMOVED*** **2. Public Access Enabled by Default**

**Why**: Practical for deployment, development, and operations.

**Security**: Use IP Access Lists or disable public access after deployment.

**Options**:
```hcl
***REMOVED*** OPTION A: Public + IP ACLs (RECOMMENDED)
enable_public_network_access = true
enable_ip_access_lists = true
allowed_ip_ranges = ["YOUR_NETWORK/24"]

***REMOVED*** OPTION B: Air-gapped (MAXIMUM SECURITY)
enable_public_network_access = false  ***REMOVED*** Requires VPN/Bastion
```

***REMOVED******REMOVED******REMOVED*** **3. Private Endpoints for Classic, Manual for Serverless**

**Terraform Creates** (Auto-Approved):
- Databricks Control Plane PE (2)
- Storage PE for classic clusters (8)

**Customer Creates** (Manual Approval):
- Storage PE for serverless (via Databricks, approved in Portal)

---

***REMOVED******REMOVED*** 📚 Reference Documentation

**Azure Official Docs**:
- [Serverless Private Link](https://learn.microsoft.com/en-us/azure/databricks/security/network/serverless-network-security/serverless-private-link)
- [Serverless Firewall](https://learn.microsoft.com/en-us/azure/databricks/security/network/serverless-network-security/serverless-firewall)
- [Private Link Setup](https://learn.microsoft.com/en-us/azure/databricks/administration-guide/cloud-configurations/azure/private-link)
- [VNet Injection](https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/vnet-inject)
- [Unity Catalog](https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/)

**Related Patterns**:
- [Non-PL Pattern](../patterns/NON-PL.md) - Public control plane + NPIP
- [AWS Full Private](../../../awsdb4u/aws-pl-ws/databricks-aws-production/docs/) - AWS equivalent

---

***REMOVED******REMOVED*** 🤝 Getting Help

**Check Deployment Status**:
```bash
cd deployments/full-private
terraform output next_steps
```

**Common Issues**:
- Workspace not accessible → Check `enable_public_network_access` and IP ACLs
- Classic cluster fails → Verify Private Endpoints created
- Serverless fails → Follow [04-SERVERLESS-SETUP.md](04-SERVERLESS-SETUP.md)
- Destroy errors → See [06-TROUBLESHOOTING.md](06-TROUBLESHOOTING.md***REMOVED***4-destroy-issues)

**Review**:
- [06-TROUBLESHOOTING.md](06-TROUBLESHOOTING.md) - Complete troubleshooting guide
- `checkpoint/FULL-PRIVATE-IMPLEMENTATION-COMPLETE.md` - Implementation details
- Deployment outputs - Next steps and guidance

---

**Pattern**: Full Private (Air-Gapped)  
**Status**: ✅ Production Ready  
**Last Updated**: 2026-01-12
