# Azure Databricks Deployment Documentation

> **Production-ready Azure Databricks workspace deployments** with Unity Catalog, networking security, and enterprise features.

---

## 🚀 Quick Start

**New to this repo?** Start here:

1. **[Quickstart Guide](01-QUICKSTART.md)** - Deploy your first workspace in 15 minutes
2. **[Deployment Checklist](02-DEPLOYMENT-CHECKLIST.md)** - Prerequisites and preparation
3. **[Choose Your Pattern](#deployment-patterns)** - Select based on your requirements

---

## 📋 Deployment Patterns

Choose the pattern that matches your security and connectivity requirements:

### [Non-Private Link](patterns/01-NON-PL.md)
**Best for:** Most deployments, cost-effective, simpler setup

- ✅ Secure Cluster Connectivity (NPIP) - No public IPs on clusters
- ✅ Unity Catalog with managed identity
- ✅ Service Endpoint Policy for storage security
- ✅ NAT Gateway for outbound connectivity
- ✅ Customer-Managed Keys (optional)
- ⚡ **Quick deployment** - Single terraform apply

**Use when:** Standard security requirements, public control plane acceptable

### [Full Private](patterns/02-FULL-PRIVATE.md)
**Best for:** Highly regulated environments, complete isolation

- ✅ All features from Non-PL pattern, PLUS:
- ✅ Private Link for control plane (front-end)
- ✅ Private Link for data plane (back-end)
- ✅ Air-gapped deployment option
- 🔒 **Complete isolation** - No public endpoints

**Use when:** Zero-trust network, compliance requirements, complete air-gapping needed

---

## 🔧 Module Reference

Deep-dive into each infrastructure component:

1. **[Networking](modules/01-NETWORKING.md)** - VNet, subnets, NSG, NAT Gateway
2. **[Workspace](modules/02-WORKSPACE.md)** - Databricks workspace configuration
3. **[Unity Catalog](modules/03-UNITY-CATALOG.md)** - Metastore, storage credentials, external locations
4. **[Network Connectivity (NCC)](modules/04-NCC.md)** - Serverless compute networking
5. **[Customer-Managed Keys (CMK)](modules/05-CMK.md)** - Encryption with your own keys
6. **[Service Endpoint Policy (SEP)](modules/06-SEP.md)** - Storage egress control

---

## 📚 How-To Guides

Step-by-step instructions for specific tasks:

### [Serverless Setup](guides/01-SERVERLESS-SETUP.md)
Enable Databricks SQL Warehouses and Serverless Notebooks with:
- Service Endpoints (recommended)
- Private Link via NCC (for complete isolation)

**Applies to:** Both Non-PL and Full-Private patterns

---

## 🛠️ Additional Documentation

### Core Documentation

- **[Traffic Flows](03-TRAFFIC-FLOWS.md)** - Network architecture and data flow diagrams
- **[Troubleshooting](04-TROUBLESHOOTING.md)** - Common issues and solutions

### Configuration

- **`terraform.tfvars.example`** - Comprehensive configuration examples in each deployment folder
- **Authentication** - Environment variables and service principal setup (see Quickstart)

---

## 📖 Documentation Structure

```
docs/
├── 01-QUICKSTART.md                 # Start here
├── 02-DEPLOYMENT-CHECKLIST.md       # Pre-deployment prep
├── 03-TRAFFIC-FLOWS.md              # Network architecture
├── 04-TROUBLESHOOTING.md            # Problem solving
│
├── patterns/                         # Deployment patterns
│   ├── 01-NON-PL.md                 # Non-Private Link
│   └── 02-FULL-PRIVATE.md           # Full Private
│
├── modules/                          # Component deep-dives
│   ├── 01-NETWORKING.md
│   ├── 02-WORKSPACE.md
│   ├── 03-UNITY-CATALOG.md
│   ├── 04-NCC.md
│   ├── 05-CMK.md
│   └── 06-SEP.md
│
└── guides/                           # How-to guides
    └── 01-SERVERLESS-SETUP.md
```

---

## 🎯 Common Workflows

### First-Time Deployment

```bash
# 1. Review prerequisites
Read: 02-DEPLOYMENT-CHECKLIST.md

# 2. Choose pattern
Non-PL: docs/patterns/01-NON-PL.md
Full-Private: docs/patterns/02-FULL-PRIVATE.md

# 3. Configure
Edit: deployments/<pattern>/terraform.tfvars

# 4. Deploy
cd deployments/<pattern>
terraform init
terraform apply

# 5. Verify
terraform output deployment_summary
```

### Enable Serverless

```bash
# After workspace deployment
Read: guides/01-SERVERLESS-SETUP.md

# Configure storage firewall or Private Link
# Test with SQL Warehouse
```

### Enable CMK Encryption

```bash
# Configure in terraform.tfvars
enable_cmk_managed_services = true
enable_cmk_managed_disks    = true
enable_cmk_dbfs_root        = true

# Apply changes
terraform apply

# Verify
terraform output customer_managed_keys
```

### Troubleshoot Issues

```bash
# Check troubleshooting guide
Read: 04-TROUBLESHOOTING.md

# Common issues:
# - Metastore deletion errors
# - Network connectivity
# - SEP/NCC destroy issues
```

---

## 🔍 Finding What You Need

### "I want to..."

- **Deploy a workspace** → [Quickstart](01-QUICKSTART.md)
- **Understand network flows** → [Traffic Flows](03-TRAFFIC-FLOWS.md)
- **Choose security options** → [Deployment Patterns](#deployment-patterns)
- **Enable encryption** → [CMK Module](modules/05-CMK.md)
- **Control storage access** → [SEP Module](modules/06-SEP.md)
- **Enable serverless** → [Serverless Setup](guides/01-SERVERLESS-SETUP.md)
- **Fix deployment issues** → [Troubleshooting](04-TROUBLESHOOTING.md)

### "I need to understand..."

- **How networking works** → [Networking Module](modules/01-NETWORKING.md)
- **Unity Catalog setup** → [Unity Catalog Module](modules/03-UNITY-CATALOG.md)
- **Workspace configuration** → [Workspace Module](modules/02-WORKSPACE.md)
- **Serverless connectivity** → [NCC Module](modules/04-NCC.md)

---

## 🏆 Best Practices

✅ **DO:**
- Start with Non-PL pattern for most deployments
- Enable Service Endpoint Policy by default
- Use Unity Catalog for all workspaces
- Tag all resources with owner and keep-until
- Test destroy workflow in non-production first
- Enable CMK for sensitive workloads

❌ **DON'T:**
- Deploy without Unity Catalog (it's mandatory)
- Skip the deployment checklist
- Disable Service Endpoint Policy without good reason
- Forget to configure serverless connectivity
- Delete resources manually (use terraform destroy)

---

## 💡 Tips for Success

### For Beginners
1. Start with [Quickstart](01-QUICKSTART.md)
2. Use Non-PL pattern
3. Keep default settings initially
4. Follow the deployment checklist
5. Join the troubleshooting guide if stuck

### For Advanced Users
1. Review [pattern comparison](patterns/) for requirements
2. Customize networking via BYOV
3. Enable all security features (CMK, SEP, Private Link)
4. Plan for serverless from the start
5. Implement hub-spoke for multiple workspaces

### For Production
1. Use service principal authentication
2. Enable all three CMK scopes
3. Test destroy workflow first
4. Document custom configurations
5. Set up monitoring and alerting
6. Plan for disaster recovery

---

## 📞 Getting Help

### Documentation Resources
- This `docs/` folder - Complete reference
- `terraform.tfvars.example` - Configuration examples
- `checkpoint/` - Implementation notes and history

### External Resources
- [Azure Databricks Documentation](https://learn.microsoft.com/en-us/azure/databricks/)
- [Databricks Terraform Provider](https://registry.terraform.io/providers/databricks/databricks/latest/docs)
- [Azure Terraform Provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)

### Support Channels
1. Check [Troubleshooting Guide](04-TROUBLESHOOTING.md) first
2. Review [checkpoint documents](../checkpoint/) for similar issues
3. Check provider documentation for recent changes
4. Contact your platform team or Databricks support

---

## 🚀 Ready to Deploy?

Start with the **[Quickstart Guide](01-QUICKSTART.md)** and have your first workspace running in 15 minutes!
