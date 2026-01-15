# Archive

This folder contains legacy content, code samples, and REST API collections that are no longer actively maintained but kept for reference.

---

## Contents

### Databricks Jump Start
**Path**: `databricks-jump-start/`

Historical code samples and tutorials covering:
- Getting started with Spark (Python, Scala, R, SQL)
- MLFlow examples
- Delta Lake examples
- Workshop materials
- Cryptography examples
- Sample datasets

**Note**: These examples may use older Databricks Runtime versions or deprecated APIs. For current best practices, see the main cloud-specific deployment guides.

### REST API Collections
**Path**: `databricks-rest-api-collection/`

Postman collections for Databricks REST APIs:
- Token management
- Cluster policies
- IP access lists
- Permissions
- Secrets management

**Note**: Consider using the [Databricks CLI](https://docs.databricks.com/dev-tools/cli/index.html) or [Terraform provider](https://registry.terraform.io/providers/databricks/databricks/latest/docs) for production automation instead of raw REST API calls.

---

## Why Archived?

These resources have been archived because:
1. **Better alternatives exist**: Modern deployment patterns use Terraform/infrastructure-as-code
2. **Maintenance burden**: Keeping examples up-to-date with every Databricks release is unsustainable
3. **Focus on production patterns**: The repository now focuses on enterprise-ready, production deployments

---

## Current Alternatives

Instead of using archived content, consider:

### For Learning Databricks
- **Databricks Academy**: https://www.databricks.com/learn/training
- **Official Documentation**: https://docs.databricks.com/
- **Databricks Community**: https://community.databricks.com/

### For Production Deployments
- **Azure**: [../adb4u/](../adb4u/) - Production-ready Terraform templates
- **AWS**: [../awsdb4u/](../awsdb4u/) - Private Link workspace deployments
- **GCP**: [../gcpdb4u/](../gcpdb4u/) - VPC-SC and PSC implementations

### For Automation
- **Terraform**: Use the [Databricks Terraform provider](https://registry.terraform.io/providers/databricks/databricks/latest/docs)
- **Databricks CLI**: For scripting and CI/CD pipelines
- **SDKs**: Python, Java, Go SDKs for programmatic access

---

## Still Useful For

These archived resources may still be useful for:
- Understanding legacy implementations
- Historical reference
- Quick code snippets (with caution)
- Learning basic concepts

**Warning**: Always verify that code examples work with your current Databricks Runtime version before using them.
