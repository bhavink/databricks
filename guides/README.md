# Databricks Cross-Cloud Guides

This folder contains cloud-agnostic guides that apply across Azure, AWS, and GCP Databricks deployments.

## Available Guides

### [Authentication Guide](./authentication.md)
**Start here if you're having trouble getting Terraform to connect to your cloud or Databricks.**

Learn how to set up authentication for Terraform so it can:
- Connect to your cloud provider (Azure/AWS/GCP)
- Connect to Databricks
- Deploy resources without permission errors

Perfect for:
- First-time Terraform users
- Troubleshooting "authentication failed" errors
- Setting up CI/CD pipelines
- Understanding which credentials go where

### [Identities & Access Guide](./identities.md)
**Understand how Databricks accesses your cloud account.**

Learn how Databricks creates workspaces and accesses storage:
- AWS: Cross-account roles and AssumeRole pattern
- Azure: First-party app and managed identities
- GCP: Service accounts and impersonation
- Unity Catalog storage access patterns
- Security model and audit trails

Perfect for:
- Understanding "how does this work?"
- Security reviews and compliance
- Troubleshooting access issues
- Explaining to management/security teams

### [Networking Guide](./networking.md)
**Understand Databricks network architecture and design secure networks.**

Learn how to design and deploy Databricks networking:
- Control plane vs compute plane architecture
- **AWS customer-managed VPC** (complete with troubleshooting)
- **Azure VNet injection** (complete with troubleshooting)
- **GCP customer-managed VPC** (complete with troubleshooting)
- VPC/VNet requirements, security rules, NAT configuration
- Private connectivity options (PrivateLink, Private Link, PSC, VPC-SC)
- Cross-cloud comparison table
- Cloud-specific troubleshooting with CLI examples
- Best practices across all three clouds

Perfect for:
- Platform engineers deploying infrastructure
- Cloud architects designing secure networks
- Security teams reviewing network controls
- Troubleshooting connectivity issues across AWS, Azure, and GCP

### [Common Questions & Answers](./common-questions.md)
**Quick answers to frequently asked questions.**

Searchable Q&A covering all Databricks topics:
- General concepts (classic vs serverless, workspace types)
- Networking (AWS, Azure, GCP-specific questions)
- Authentication & identity (coming soon)
- Security & compliance
- Troubleshooting common issues

Perfect for:
- Quick reference when stuck
- Understanding specific concepts
- Comparing options across clouds
- Troubleshooting guidance

---

## Coming Soon

- **Security Guide** - Best practices for secure Databricks deployments
- **Performance Guide** - Optimization and tuning recommendations

---

## How to Use These Guides

1. Start with the topic you need help with
2. Each guide is written in plain English (no jargon)
3. Follow the step-by-step instructions
4. Copy-paste the examples
5. Refer back when you get stuck

---

## Feedback

Found something confusing? Please let us know so we can improve these guides.
