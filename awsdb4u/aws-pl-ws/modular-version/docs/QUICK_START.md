***REMOVED*** ⚡ Quick Start Guide

Get up and running in 5 minutes!

***REMOVED******REMOVED*** 1. Prerequisites Check

```bash
***REMOVED*** Check Terraform
terraform --version  ***REMOVED*** Should be >= 1.0

***REMOVED*** Check AWS CLI
aws --version

***REMOVED*** Check AWS credentials (use your profile or default)
aws sts get-caller-identity --profile your-profile-name
***REMOVED*** OR for default credentials:
***REMOVED*** aws sts get-caller-identity
```

***REMOVED******REMOVED*** 2. AWS Authentication

Choose one option:

**Option A: Named Profile** (recommended)
```bash
aws configure --profile your-profile-name
```

**Option B: Default Credentials**
```bash
aws configure
***REMOVED*** OR
aws sso login
```

***REMOVED******REMOVED*** 3. Configure

Edit `terraform.tfvars`:

```hcl
***REMOVED*** Required minimum configuration
client_id             = "your-sp-client-id"
client_secret         = "your-sp-secret"
databricks_account_id = "your-account-id"
aws_account_id        = "123456789012"
aws_profile           = "your-profile-name"  ***REMOVED*** or leave empty for default
workspace_name        = "my-workspace"
workspace_admin_email = "admin@company.com"

***REMOVED*** Customize S3 bucket names (must be globally unique)
root_storage_bucket_name                = "mycompany-dbx-root"
unity_catalog_bucket_name               = "mycompany-dbx-uc-metastore"
unity_catalog_external_bucket_name      = "mycompany-dbx-uc-external"
unity_catalog_root_storage_bucket_name  = "mycompany-dbx-uc-root-storage"
```

***REMOVED******REMOVED*** 4. Deploy

```bash
cd modular-version

***REMOVED*** Initialize
terraform init

***REMOVED*** Plan (optional but recommended)
terraform plan

***REMOVED*** Deploy
terraform apply
***REMOVED*** Type 'yes' when prompted
```

⏰ **Wait:** 10-15 minutes for deployment to complete.

***REMOVED******REMOVED*** 5. Access

```bash
***REMOVED*** Get workspace URL
terraform output workspace_url

***REMOVED*** Get deployment summary
terraform output deployment_summary
```

⏰ **IMPORTANT:** Wait 20 minutes before creating clusters!

***REMOVED******REMOVED*** 6. Verify

1. Open workspace URL in browser
2. Log in with your admin email
3. Navigate to "Data" → See your catalog
4. Create a test cluster (after 20 min wait)

***REMOVED******REMOVED*** 7. Clean Up (When Done)

```bash
***REMOVED*** Quick destroy
terraform destroy
***REMOVED*** Type 'yes' when prompted
```

---

***REMOVED******REMOVED*** 📁 What You Get

- ✅ Fully private Databricks workspace
- ✅ VPC with 3 subnet tiers (public, private, privatelink)
- ✅ NAT Gateways in 2 AZs for HA
- ✅ Security groups configured
- ✅ VPC endpoints (S3, STS, Kinesis, Workspace, Relay)
- ✅ Unity Catalog with metastore
- ✅ Workspace catalog with storage
- ✅ External location for data access
- ✅ Workspace admin with full privileges

***REMOVED******REMOVED*** 🔧 Common Customizations

***REMOVED******REMOVED******REMOVED*** Use Different Region

```hcl
region = "us-east-1"
availability_zones = ["us-east-1a", "us-east-1b"]
```

***REMOVED******REMOVED******REMOVED*** Enable KMS Encryption

```hcl
enable_encryption = true
```

***REMOVED******REMOVED******REMOVED*** Customize VPC CIDR

```hcl
vpc_cidr                 = "172.16.0.0/16"
private_subnet_cidrs     = ["172.16.1.0/24", "172.16.2.0/24"]
privatelink_subnet_cidrs = ["172.16.3.0/24", "172.16.4.0/24"]
public_subnet_cidrs      = ["172.16.101.0/24", "172.16.102.0/24"]
```

***REMOVED******REMOVED*** 🐛 Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| Credential errors | `aws sso login --profile your-profile` |
| Bucket exists | Change bucket names in `terraform.tfvars` |
| Can't access workspace | Wait 20 minutes for Private Link |
| Provider errors | Run `terraform init` |

***REMOVED******REMOVED*** 📚 More Details

For detailed instructions, see:
- `USAGE_GUIDE.md` - Complete step-by-step guide
- `README.md` - Architecture and module overview
- `modules/*/README.md` - Individual module documentation

---

**That's it!** You now have a production-ready Databricks workspace with Private Link and Unity Catalog. 🎉

