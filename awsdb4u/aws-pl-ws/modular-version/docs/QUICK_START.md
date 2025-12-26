# ⚡ Quick Start Guide

Get up and running in 5 minutes!

## 1. Prerequisites Check

```bash
# Check Terraform
terraform --version  # Should be >= 1.0

# Check AWS CLI
aws --version

# Check AWS credentials (use your profile or default)
aws sts get-caller-identity --profile your-profile-name
# OR for default credentials:
# aws sts get-caller-identity
```

## 2. AWS Authentication

Choose one option:

**Option A: Named Profile** (recommended)
```bash
aws configure --profile your-profile-name
```

**Option B: Default Credentials**
```bash
aws configure
# OR
aws sso login
```

## 3. Configure

Edit `terraform.tfvars`:

```hcl
# Required minimum configuration
client_id             = "your-sp-client-id"
client_secret         = "your-sp-secret"
databricks_account_id = "your-account-id"
aws_account_id        = "123456789012"
aws_profile           = "your-profile-name"  # or leave empty for default
workspace_name        = "my-workspace"
workspace_admin_email = "admin@company.com"

# Customize S3 bucket names (must be globally unique)
root_storage_bucket_name                = "mycompany-dbx-root"
unity_catalog_bucket_name               = "mycompany-dbx-uc-metastore"
unity_catalog_external_bucket_name      = "mycompany-dbx-uc-external"
unity_catalog_root_storage_bucket_name  = "mycompany-dbx-uc-root-storage"
```

## 4. Deploy

```bash
cd modular-version

# Initialize
terraform init

# Plan (optional but recommended)
terraform plan

# Deploy
terraform apply
# Type 'yes' when prompted
```

⏰ **Wait:** 10-15 minutes for deployment to complete.

## 5. Access

```bash
# Get workspace URL
terraform output workspace_url

# Get deployment summary
terraform output deployment_summary
```

⏰ **IMPORTANT:** Wait 20 minutes before creating clusters!

## 6. Verify

1. Open workspace URL in browser
2. Log in with your admin email
3. Navigate to "Data" → See your catalog
4. Create a test cluster (after 20 min wait)

## 7. Clean Up (When Done)

```bash
# Quick destroy
terraform destroy
# Type 'yes' when prompted
```

---

## 📁 What You Get

- ✅ Fully private Databricks workspace
- ✅ VPC with 3 subnet tiers (public, private, privatelink)
- ✅ NAT Gateways in 2 AZs for HA
- ✅ Security groups configured
- ✅ VPC endpoints (S3, STS, Kinesis, Workspace, Relay)
- ✅ Unity Catalog with metastore
- ✅ Workspace catalog with storage
- ✅ External location for data access
- ✅ Workspace admin with full privileges

## 🔧 Common Customizations

### Use Different Region

```hcl
region = "us-east-1"
availability_zones = ["us-east-1a", "us-east-1b"]
```

### Enable KMS Encryption

```hcl
enable_encryption = true
```

### Customize VPC CIDR

```hcl
vpc_cidr                 = "172.16.0.0/16"
private_subnet_cidrs     = ["172.16.1.0/24", "172.16.2.0/24"]
privatelink_subnet_cidrs = ["172.16.3.0/24", "172.16.4.0/24"]
public_subnet_cidrs      = ["172.16.101.0/24", "172.16.102.0/24"]
```

## 🐛 Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| Credential errors | `aws sso login --profile your-profile` |
| Bucket exists | Change bucket names in `terraform.tfvars` |
| Can't access workspace | Wait 20 minutes for Private Link |
| Provider errors | Run `terraform init` |

## 📚 More Details

For detailed instructions, see:
- `USAGE_GUIDE.md` - Complete step-by-step guide
- `README.md` - Architecture and module overview
- `modules/*/README.md` - Individual module documentation

---

**That's it!** You now have a production-ready Databricks workspace with Private Link and Unity Catalog. 🎉

