Azure Databricks Security Best Practices
==============
- Documenting and sharing security best practices related to platform deployment and configuration.
- [Security Guide](https://bit.ly/adbsecurityguide)

## 🚀 New Modular Terraform Structure

This repository provides **production-ready, modular Terraform templates** for Azure Databricks deployments.

### 📁 Repository Structure

```
adb4u/
├── docs/                      # 📚 All documentation centralized here
│   ├── README.md              # Documentation index
│   ├── 01-QUICKSTART.md       # Quick start guide
│   ├── TROUBLESHOOTING.md     # ⚠️ Common issues & solutions
│   ├── DEPLOYMENT-CHECKLIST.md # Pre-flight checklist
│   ├── 03-AUTHENTICATION.md   # Authentication setup
│   ├── modules/               # Module documentation
│   └── patterns/              # Pattern-specific guides
│
├── deployments/               # Pre-built deployment patterns
│   ├── non-pl/                # ✅ Non-Private Link (Ready)
│   ├── full-private/          # 🚧 Full Private (Coming soon)
│   └── hub-spoke/             # 🚧 Hub-Spoke (Future)
│
├── modules/                   # Reusable Terraform modules
│   ├── networking/            # VNet, subnets, NSG, NAT
│   ├── workspace/             # Databricks workspace
│   └── unity-catalog/         # Metastore, storage, credentials
│
└── templates/                 # Legacy templates (reference only)
```

### 🎯 Deployment Patterns

#### 1. **Non-Private Link (Non-PL)** ✅ Production Ready
- **Control Plane**: Public
- **Data Plane**: Private (NPIP)
- **Egress**: NAT Gateway
- **Storage**: Service Endpoints
- **Cost**: ~$58/month

👉 **[Quick Start Guide →](./docs/01-QUICKSTART.md)**  
⚠️ **[Troubleshooting Guide →](./docs/TROUBLESHOOTING.md)** - Review before deploying!

#### 2. **Full Private (Air-gapped)** 🚧 Coming Soon
- **Control Plane**: Private Link
- **Data Plane**: Private (NPIP)
- **Egress**: None (isolated)
- **Storage**: Private Link
- **Cost**: ~$100/month

#### 3. **Hub-Spoke with Firewall** 🚧 Future
- Enterprise-scale multi-workspace deployments

### ✨ Key Features

- ✅ **Secure Cluster Connectivity (NPIP)**: Always enabled
- ✅ **Unity Catalog**: Mandatory, regional metastore
- ✅ **Flexible Networking**: Create new or BYOV
- ✅ **Service Endpoint Policies**: Enhanced storage security
- ✅ **Modular Design**: Reusable, composable components
- ✅ **Well-Documented**: Comprehensive guides in `/docs`

### 🚀 Quick Start

```bash
# Navigate to deployment
cd deployments/non-pl

# Configure
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# Deploy
export TF_VAR_databricks_account_id="<your-account-id>"
terraform init
terraform plan
terraform apply
```

**Full guide:** See [docs/01-QUICKSTART.md](./docs/01-QUICKSTART.md)

### 📚 Documentation

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

## 📦 Legacy Content

Historical content and diagrams have been archived. See **[archive/LEGACY-CONTENT.md](./archive/LEGACY-CONTENT.md)** for reference.

**For new deployments, use the modular structure documented above.**

---

**Repository Version**: 2.0  
**Last Updated**: 2026-01-10  
**Security Guide**: [https://bit.ly/adbsecurityguide](https://bit.ly/adbsecurityguide)
