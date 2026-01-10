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
│   ├── full-private/          ***REMOVED*** 🚧 Full Private (Coming soon)
│   └── hub-spoke/             ***REMOVED*** 🚧 Hub-Spoke (Future)
│
├── modules/                   ***REMOVED*** Reusable Terraform modules
│   ├── networking/            ***REMOVED*** VNet, subnets, NSG, NAT
│   ├── workspace/             ***REMOVED*** Databricks workspace
│   └── unity-catalog/         ***REMOVED*** Metastore, storage, credentials
│
└── templates/                 ***REMOVED*** Legacy templates (reference only)
```

***REMOVED******REMOVED******REMOVED*** 🎯 Deployment Patterns

***REMOVED******REMOVED******REMOVED******REMOVED*** 1. **Non-Private Link (Non-PL)** ✅ Production Ready
- **Control Plane**: Public
- **Data Plane**: Private (NPIP)
- **Egress**: NAT Gateway
- **Storage**: Service Endpoints
- **Cost**: ~$58/month

👉 **[Quick Start Guide →](./docs/01-QUICKSTART.md)**  
⚠️ **[Troubleshooting Guide →](./docs/TROUBLESHOOTING.md)** - Review before deploying!

***REMOVED******REMOVED******REMOVED******REMOVED*** 2. **Full Private (Air-gapped)** 🚧 Coming Soon
- **Control Plane**: Private Link
- **Data Plane**: Private (NPIP)
- **Egress**: None (isolated)
- **Storage**: Private Link
- **Cost**: ~$100/month

***REMOVED******REMOVED******REMOVED******REMOVED*** 3. **Hub-Spoke with Firewall** 🚧 Future
- Enterprise-scale multi-workspace deployments

***REMOVED******REMOVED******REMOVED*** ✨ Key Features

- ✅ **Secure Cluster Connectivity (NPIP)**: Always enabled
- ✅ **Unity Catalog**: Mandatory, regional metastore
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

***REMOVED******REMOVED******REMOVED*** 📚 Documentation

All documentation is centralized in the **[docs/](./docs/)** folder:

- **[Quick Start Guide](./docs/01-QUICKSTART.md)** - Deploy your first workspace
- **[Troubleshooting Guide](./docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Traffic Flows](./docs/TRAFFIC-FLOWS.md)** - Network traffic patterns and sequences
- **[Deployment Checklist](./docs/DEPLOYMENT-CHECKLIST.md)** - Pre-flight validation
- **[Authentication Guide](./docs/03-AUTHENTICATION.md)** - Configure credentials
- **[Module Documentation](./docs/modules/)** - Detailed module reference
  - [Networking Module](./docs/modules/NETWORKING.md)
  - [Workspace Module](./docs/modules/WORKSPACE.md)
  - [Unity Catalog Module](./docs/modules/UNITY-CATALOG.md)
- **[Pattern Guides](./docs/patterns/)** - Pattern-specific documentation
  - [Non-PL Pattern](./docs/patterns/NON-PL.md)

---

***REMOVED******REMOVED*** 📦 Legacy Content

Historical content and diagrams have been archived. See **[archive/LEGACY-CONTENT.md](./archive/LEGACY-CONTENT.md)** for reference.

**For new deployments, use the modular structure documented above.**

---

**Repository Version**: 2.0  
**Last Updated**: 2026-01-10  
**Security Guide**: [https://bit.ly/adbsecurityguide](https://bit.ly/adbsecurityguide)
