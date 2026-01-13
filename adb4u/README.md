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
│   ├── TROUBLESHOOTING.md     ***REMOVED*** ⚠️ Common issues & solutions
│   ├── DEPLOYMENT-CHECKLIST.md ***REMOVED*** Pre-flight checklist
│   ├── 03-AUTHENTICATION.md   ***REMOVED*** Authentication setup
│   ├── modules/               ***REMOVED*** Module documentation
│   └── patterns/              ***REMOVED*** Pattern-specific guides
│
├── deployments/               ***REMOVED*** Pre-built deployment patterns
│   ├── non-pl/                ***REMOVED*** ✅ Non-Private Link (Ready)
│   ├── full-private/          ***REMOVED*** ✅ Full Private (Ready)
│   └── hub-spoke/             ***REMOVED*** 🚧 Hub-Spoke (Future)
│
├── modules/                   ***REMOVED*** Reusable Terraform modules
│   ├── networking/            ***REMOVED*** VNet, subnets, NSG, NAT
│   ├── workspace/             ***REMOVED*** Databricks workspace
│   ├── unity-catalog/         ***REMOVED*** Metastore, storage, credentials
│   └── ncc/                   ***REMOVED*** Network Connectivity Config (serverless)
│
└── templates/                 ***REMOVED*** Legacy templates (reference only)
```

***REMOVED******REMOVED******REMOVED*** 🎯 Deployment Patterns

***REMOVED******REMOVED******REMOVED******REMOVED*** 1. **Non-Private Link (Non-PL)** ✅ Production Ready
- **Control Plane**: Public
- **Data Plane**: Private (NPIP)
- **Egress**: NAT Gateway
- **Storage**: Service Endpoints
- **Serverless**: NCC attached (Service Endpoints or Private Link)

👉 **[Quick Start Guide →](./docs/01-QUICKSTART.md)**  
🚀 **[Serverless Setup →](./deployments/non-pl/docs/SERVERLESS-SETUP.md)**  
⚠️ **[Troubleshooting Guide →](./docs/TROUBLESHOOTING.md)** - Review before deploying!

***REMOVED******REMOVED******REMOVED******REMOVED*** 2. **Full Private (Air-gapped)** ✅ Production Ready
- **Workspace Access**: Private Link (SCC relay + API)
- **Data Plane**: Private (NPIP)
- **Egress**: None (isolated)
- **Storage**: Private Link
- **Serverless**: NCC attached (Private Link required)

👉 **[Full Documentation →](./deployments/full-private/docs/README.md)**  
🚀 **[Serverless Setup →](./deployments/full-private/docs/04-SERVERLESS-SETUP.md)**  
⚠️ **[Troubleshooting Guide →](./deployments/full-private/docs/06-TROUBLESHOOTING.md)** - Common issues & solutions!

***REMOVED******REMOVED******REMOVED******REMOVED*** 3. **Hub-Spoke with Firewall** 🚧 Future
- Enterprise-scale multi-workspace deployments

***REMOVED******REMOVED******REMOVED*** ✨ Key Features

- ✅ **Secure Cluster Connectivity (NPIP)**: Always enabled
- ✅ **Unity Catalog**: Mandatory, regional metastore
- ✅ **Network Connectivity Config (NCC)**: Mandatory for serverless compute
- ✅ **Flexible Networking**: Create new or BYOV
- ✅ **Service Endpoint Policies**: Enhanced storage security
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

**Post-Deployment Setup**:
- 📖 **Non-PL**: See [deployments/non-pl/docs/SERVERLESS-SETUP.md](./deployments/non-pl/docs/SERVERLESS-SETUP.md)
- 📖 **Full Private**: See [deployments/full-private/docs/04-SERVERLESS-SETUP.md](./deployments/full-private/docs/04-SERVERLESS-SETUP.md)

**Key Points**:
- ✅ NCC is **mandatory** (created automatically like Unity Catalog)
- ✅ Classic clusters work immediately after deployment
- ⏸️ Serverless requires additional configuration (manual approval for Private Link)

***REMOVED******REMOVED******REMOVED*** 📚 Documentation

All documentation is centralized in the **[docs/](./docs/)** folder:

**Non-PL Pattern (Production Ready)**:
- **[Quick Start Guide](./docs/01-QUICKSTART.md)** - Deploy your first workspace
- **[Serverless Setup](./deployments/non-pl/docs/SERVERLESS-SETUP.md)** - Enable SQL Warehouses & Notebooks
- **[Troubleshooting Guide](./docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Traffic Flows](./docs/TRAFFIC-FLOWS.md)** - Network traffic patterns and sequences
- **[Deployment Checklist](./docs/DEPLOYMENT-CHECKLIST.md)** - Pre-flight validation
- **[Authentication Guide](./docs/03-AUTHENTICATION.md)** - Configure credentials

**Full Private Pattern (Production Ready)**:
- **[Complete Documentation Index](./deployments/full-private/docs/README.md)** - Start here
- **[Architecture Overview](./deployments/full-private/docs/01-ARCHITECTURE.md)** - Visual diagrams
- **[Serverless Setup Guide](./deployments/full-private/docs/04-SERVERLESS-SETUP.md)** - Enable serverless compute
- **[Troubleshooting Guide](./deployments/full-private/docs/06-TROUBLESHOOTING.md)** - Errors & solutions

**Module Documentation**:
- **[Module Documentation](./docs/modules/)** - Detailed module reference
  - [Networking Module](./docs/modules/NETWORKING.md)
  - [Workspace Module](./docs/modules/WORKSPACE.md)
  - [Unity Catalog Module](./docs/modules/UNITY-CATALOG.md)
  - [NCC Module](./docs/modules/NCC.md) - Network Connectivity Configuration

**Pattern Guides**:
- **[Pattern Guides](./docs/patterns/)** - Pattern-specific documentation
  - [Non-PL Pattern](./docs/patterns/NON-PL.md)

---

***REMOVED******REMOVED*** 📦 Legacy Content

Historical content and diagrams have been archived. See **[archive/LEGACY-CONTENT.md](./archive/LEGACY-CONTENT.md)** for reference.

**For new deployments, use the modular structure documented above.**

---

**Repository Version**: 2.0
