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

---

## Coming Soon

- **Networking Guide** - VPCs, subnets, private endpoints explained simply
- **Security Guide** - Best practices for secure Databricks deployments
- **Troubleshooting Guide** - Common errors and how to fix them

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
