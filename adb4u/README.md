Azure Databricks Security Best Practices
==============
**Production-ready, modular Terraform templates** for secure Azure Databricks deployments.

📚 **[Complete Documentation →](./docs/)**

---

***REMOVED******REMOVED*** 🚀 Modular Terraform Structure

This repository provides **production-ready, modular Terraform templates** for Azure Databricks deployments with comprehensive documentation, UML diagrams, and troubleshooting guides.

***REMOVED******REMOVED******REMOVED*** 📁 Repository Structure

```
adb4u/
├── docs/                      ***REMOVED*** 📚 All documentation centralized here
│   ├── README.md              ***REMOVED*** Documentation index
│   ├── 01-QUICKSTART.md       ***REMOVED*** Quick start guide
│   ├── 02-DEPLOYMENT-CHECKLIST.md ***REMOVED*** Pre-flight checklist
│   ├── 03-TRAFFIC-FLOWS.md    ***REMOVED*** Network traffic patterns
│   ├── 04-TROUBLESHOOTING.md  ***REMOVED*** ⚠️ Common issues & solutions
│   ├── guides/                ***REMOVED*** Additional guides
│   │   └── 01-SERVERLESS-SETUP.md
│   ├── modules/               ***REMOVED*** Module documentation
│   │   ├── 01-NETWORKING.md
│   │   ├── 02-WORKSPACE.md
│   │   ├── 03-UNITY-CATALOG.md
│   │   ├── 04-NCC.md
│   │   ├── 05-CMK.md
│   │   └── 06-SEP.md
│   └── patterns/              ***REMOVED*** Pattern-specific guides
│       ├── 01-NON-PL.md
│       └── 02-FULL-PRIVATE.md
│
├── deployments/               ***REMOVED*** Pre-built deployment patterns
│   ├── non-pl/                ***REMOVED*** ✅ Non-Private Link (Ready)
│   ├── full-private/          ***REMOVED*** ✅ Full Private (Ready)
│   ├── byor/                  ***REMOVED*** ✅ Bring Your Own Resources (Ready)
│   └── hub-spoke/             ***REMOVED*** 🚧 Hub-Spoke (Future)
│
├── modules/                   ***REMOVED*** Reusable Terraform modules
│   ├── networking/            ***REMOVED*** VNet, subnets, NSG, NAT
│   ├── workspace/             ***REMOVED*** Databricks workspace
│   ├── unity-catalog/         ***REMOVED*** Metastore, storage, credentials
│   ├── ncc/                   ***REMOVED*** Network Connectivity Config (serverless)
│   ├── key-vault/             ***REMOVED*** Azure Key Vault integration
│   ├── private-endpoints/     ***REMOVED*** Private Link endpoints
│   ├── service-endpoint-policy/ ***REMOVED*** Service Endpoint Policies
│   ├── security/              ***REMOVED*** Security modules (CMK, IP access lists)
│   └── monitoring/            ***REMOVED*** Monitoring and observability
│
└── archive/                   ***REMOVED*** Legacy content and templates
    └── LEGACY-CONTENT.md      ***REMOVED*** Historical reference
```

***REMOVED******REMOVED******REMOVED*** 🎯 Deployment Patterns

***REMOVED******REMOVED******REMOVED******REMOVED*** 1. **Non-Private Link (Non-PL)** ✅ Production Ready
- **Control Plane**: Public
- **Data Plane**: Private (NPIP)
- **Egress**: NAT Gateway
- **Storage**: Service Endpoints
- **Serverless**: NCC attached (Service Endpoints or Private Link)

👉 **[Quick Start Guide →](./docs/01-QUICKSTART.md)**  
🚀 **[Serverless Setup →](./docs/guides/01-SERVERLESS-SETUP.md)**  
⚠️ **[Troubleshooting Guide →](./docs/04-TROUBLESHOOTING.md)** - Review before deploying!

***REMOVED******REMOVED******REMOVED******REMOVED*** 2. **Full Private (Air-gapped)** ✅ Production Ready
- **Workspace Access**: Private Link (SCC relay + API)
- **Data Plane**: Private (NPIP)
- **Egress**: None (isolated)
- **Storage**: Private Link
- **Serverless**: NCC attached (Private Link required)

👉 **[Pattern Documentation →](./docs/patterns/02-FULL-PRIVATE.md)**  
🚀 **[Serverless Setup →](./docs/guides/01-SERVERLESS-SETUP.md)**  
⚠️ **[Troubleshooting Guide →](./docs/04-TROUBLESHOOTING.md)** - Common issues & solutions!

***REMOVED******REMOVED******REMOVED******REMOVED*** 3. **BYOR (Bring Your Own Resources)** ✅ Production Ready
- Integrate with existing Azure infrastructure
- Bring your own VNet, Storage Account, Key Vault
- Customer-Managed Keys (CMK) for enhanced security
- Flexible configuration for existing environments

👉 **[BYOR Documentation →](./deployments/byor/README.md)**

***REMOVED******REMOVED******REMOVED******REMOVED*** 4. **Hub-Spoke with Firewall** 🚧 Future
- Enterprise-scale multi-workspace deployments

***REMOVED******REMOVED******REMOVED*** ✨ Key Features

- ✅ **Secure Cluster Connectivity (NPIP)**: Always enabled
- ✅ **Unity Catalog**: Mandatory, regional metastore
- ✅ **Network Connectivity Config (NCC)**: Mandatory for serverless compute
- ✅ **Flexible Networking**: Create new or BYOV
- ✅ **Service Endpoint Policies**: Enhanced storage security
- ✅ **Customer-Managed Keys (CMK)**: Optional encryption control
- ✅ **Private Link Support**: Full private connectivity option
- ✅ **BYOR Support**: Integrate with existing infrastructure
- ✅ **Modular Design**: Reusable, composable components
- ✅ **Well-Documented**: Comprehensive guides in `/docs`

***REMOVED******REMOVED******REMOVED*** 🚀 Quick Start

```bash
***REMOVED*** Navigate to deployment
cd deployments/non-pl

***REMOVED*** Configure
cp terraform.tfvars.example terraform.tfvars
***REMOVED*** Edit terraform.tfvars with your values

***REMOVED*** Deploy
export TF_VAR_databricks_account_id="<your-account-id>"
terraform init
terraform plan
terraform apply
```

**Full guide:** See [docs/01-QUICKSTART.md](./docs/01-QUICKSTART.md)

***REMOVED******REMOVED******REMOVED*** 🚀 Serverless Compute

**All deployments include Network Connectivity Configuration (NCC)** for serverless SQL Warehouses and Serverless Notebooks.

***REMOVED******REMOVED******REMOVED******REMOVED*** **Serverless Connectivity Options**:

| Pattern | Classic Clusters | Serverless Compute |
|---------|------------------|-------------------|
| **Non-PL** | Service Endpoints (VNet) | Service Endpoints or Private Link (via NCC) |
| **Full Private** | Private Endpoints (VNet) | Private Link (via NCC) |
| **BYOR** | Flexible (based on existing setup) | Configurable via NCC |

**Post-Deployment Setup**:
- 📖 **Serverless Setup**: See [docs/guides/01-SERVERLESS-SETUP.md](./docs/guides/01-SERVERLESS-SETUP.md)

**Key Points**:
- ✅ NCC is **mandatory** (created automatically like Unity Catalog)
- ✅ Classic clusters work immediately after deployment
- ⏸️ Serverless requires additional configuration (manual approval for Private Link)

***REMOVED******REMOVED******REMOVED*** 📚 Documentation

All documentation is centralized in the **[docs/](./docs/)** folder:

**Getting Started**:
- **[Quick Start Guide](./docs/01-QUICKSTART.md)** - Deploy your first workspace
- **[Deployment Checklist](./docs/02-DEPLOYMENT-CHECKLIST.md)** - Pre-flight validation
- **[Traffic Flows](./docs/03-TRAFFIC-FLOWS.md)** - Network traffic patterns and sequences
- **[Troubleshooting Guide](./docs/04-TROUBLESHOOTING.md)** - Common issues and solutions

**Guides**:
- **[Serverless Setup Guide](./docs/guides/01-SERVERLESS-SETUP.md)** - Enable SQL Warehouses & Notebooks

**Pattern Documentation**:
- **[Non-PL Pattern](./docs/patterns/01-NON-PL.md)** - Non-Private Link deployment
- **[Full Private Pattern](./docs/patterns/02-FULL-PRIVATE.md)** - Air-gapped deployment

**Module Documentation**:
- **[Networking Module](./docs/modules/01-NETWORKING.md)** - VNet, subnets, NSG, NAT
- **[Workspace Module](./docs/modules/02-WORKSPACE.md)** - Databricks workspace configuration
- **[Unity Catalog Module](./docs/modules/03-UNITY-CATALOG.md)** - Metastore and catalogs
- **[NCC Module](./docs/modules/04-NCC.md)** - Network Connectivity Configuration
- **[CMK Module](./docs/modules/05-CMK.md)** - Customer-Managed Keys
- **[SEP Module](./docs/modules/06-SEP.md)** - Service Endpoint Policies

---

***REMOVED******REMOVED*** 📦 Legacy Content

Historical content and diagrams have been archived. See **[archive/LEGACY-CONTENT.md](./archive/LEGACY-CONTENT.md)** for reference.

**For new deployments, use the modular structure documented above.**

---

**Repository Version**: 2.0
