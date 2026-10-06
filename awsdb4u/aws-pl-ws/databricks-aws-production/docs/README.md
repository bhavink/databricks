# Databricks AWS Deployment - Documentation Index

> **Start Here**: Complete visual guide for deploying secure Databricks workspaces on AWS.

## Documentation Structure

```
Visual-First Documentation:
├── 00-PREREQUISITES.md      → System setup & credentials
├── 01-ARCHITECTURE.md        → Architecture & deployment flow
├── 02-IAM-SECURITY.md        → IAM roles & policies
├── 03-NETWORK-ENCRYPTION.md  → Network security & encryption
├── 04-QUICK-START.md         → 5-minute deployment guide
└── 05-TROUBLESHOOTING.md     → Common issues & solutions

Archived Documentation (Advanced Reference):
└── archive/
    ├── DEPLOYMENT_GUIDE.md      → Detailed deployment walkthrough
    ├── DEPLOYMENT_ORDER_FIX.md  → Unity Catalog dependency patterns
    └── DESTROY_GUIDE.md         → Safe resource cleanup procedures
```

---

## Quick Navigation

**First Time User?**
1. [00-PREREQUISITES.md](00-PREREQUISITES.md) - Set up your system
2. [04-QUICK-START.md](04-QUICK-START.md) - Deploy in 5 minutes
3. [05-TROUBLESHOOTING.md](05-TROUBLESHOOTING.md) - If you hit issues

**Want to Understand the System?**
1. [01-ARCHITECTURE.md](01-ARCHITECTURE.md) - See the big picture
2. [02-IAM-SECURITY.md](02-IAM-SECURITY.md) - Understand IAM roles
3. [03-NETWORK-ENCRYPTION.md](03-NETWORK-ENCRYPTION.md) - Learn security & traffic flows

**Having Problems?**
- [05-TROUBLESHOOTING.md](05-TROUBLESHOOTING.md) - Search for your error message

---

## Document Summaries

### [00-PREREQUISITES.md](00-PREREQUISITES.md)
**Before You Begin**: System requirements, tool installation, credential configuration
- Databricks E2 account setup
- Service Principal creation
- AWS authentication (4 options)
- Terraform & AWS CLI installation
- Environment variable configuration
- Pre-flight checklist

### [01-ARCHITECTURE.md](01-ARCHITECTURE.md)
**Architecture Overview**: Complete system design with modular visual diagrams
- High-level architecture (VPC, subnets, endpoints)
- Module dependency flow (7 modules)
- VPC & network layout (3 subnet tiers)
- Deployment sequence diagrams
- Resource breakdown (65-70 resources)
- Configuration scenarios

### [02-IAM-SECURITY.md](02-IAM-SECURITY.md)
**IAM & Security**: Roles, policies, and permissions categorized by creation order
- IAM role hierarchy & trust relationships
- Cross-account role (Databricks control plane)
- Unity Catalog roles (metastore + external)
- Instance profile role (cluster compute)
- KMS encryption policies
- Pre-creation guide
- Security best practices

### [03-NETWORK-ENCRYPTION.md](03-NETWORK-ENCRYPTION.md)
**Network & Encryption**: Traffic flows, security groups, encryption layers
- Traffic flow patterns (sequences)
- Security group rules (workspace + VPCE)
- Dual encryption architecture (S3 + Workspace CMK)
- Private Link vs public internet comparison
- Port requirements (8443-8451, 6666)
- DNS resolution logic

### [04-QUICK-START.md](04-QUICK-START.md)
**Quick Deployment**: Minimal steps to get running fast
- 3-step deployment process
- Configuration examples
- Common customizations
- What gets created
- Clean up instructions
- Quick troubleshooting table

### [05-TROUBLESHOOTING.md](05-TROUBLESHOOTING.md)
**Problem Solving**: Common issues, error messages, solutions
- Setup issues (Terraform, AWS CLI, credentials)
- Terraform errors (validation, arguments)
- AWS errors (S3, VPC, KMS)
- Databricks errors (authentication, permissions)
- Encryption issues (KMS, key rotation)
- Destroy issues (VPC dependencies, ENIs)
- Getting more help

---

## Use Cases

### "I just want to deploy quickly"
→ [04-QUICK-START.md](04-QUICK-START.md)

### "I need to understand how it works"
→ [01-ARCHITECTURE.md](01-ARCHITECTURE.md)

### "I'm getting an error"
→ [05-TROUBLESHOOTING.md](05-TROUBLESHOOTING.md)

### "I need to explain this to my security team"
→ [02-IAM-SECURITY.md](02-IAM-SECURITY.md) + [03-NETWORK-ENCRYPTION.md](03-NETWORK-ENCRYPTION.md)

### "I'm setting up my laptop"
→ [00-PREREQUISITES.md](00-PREREQUISITES.md)

---

## Related Documentation

**External Links**:
- [Databricks AWS Documentation](https://docs.databricks.com/aws/en/)
- [Databricks Private Link](https://docs.databricks.com/aws/en/security/network/classic/privatelink.html)
- [Unity Catalog Setup](https://docs.databricks.com/aws/en/data-governance/unity-catalog/)
- [Customer-Managed Keys](https://docs.databricks.com/aws/en/security/keys/)
- [Terraform Databricks Provider](https://registry.terraform.io/providers/databricks/databricks/latest/docs)

**Project Files**:
- `../terraform.tfvars` - Your configuration
- `../main.tf` - Module orchestration
- `../modules/` - 7 Terraform modules

---

## Documentation Updates

**Latest Changes**:
- Visual-first approach with modular Mermaid diagrams
- IAM roles categorized by creation order
- Network traffic flows with sequence diagrams
- KMS encryption layers clearly separated
- Quick troubleshooting with searchable error patterns
- Cloud-agnostic structure (applies to Azure/GCP)
- Streamlined archive (3 operational references only)

**Version**: 2026-01-08

---

## Best Practices

1. **Read Prerequisites First**: Don't skip [00-PREREQUISITES.md](00-PREREQUISITES.md)
2. **Use Quick Start for First Deploy**: [04-QUICK-START.md](04-QUICK-START.md)
3. **Keep Troubleshooting Open**: Bookmark [05-TROUBLESHOOTING.md](05-TROUBLESHOOTING.md)
4. **Understand Before Customizing**: Read [01-ARCHITECTURE.md](01-ARCHITECTURE.md)
5. **Search Documentation**: Use Ctrl+F to find specific errors or topics

---

## Contributing

Found an issue or have a suggestion?
- Document problems in [05-TROUBLESHOOTING.md](05-TROUBLESHOOTING.md)
- Suggest improvements via issues
- Follow the visual-first documentation pattern

---

**Ready to Deploy?** → [04-QUICK-START.md](04-QUICK-START.md)
