# AWS Databricks Private Link - Modular Version

This is the **modular version** of the AWS Databricks Private Link deployment. It uses Terraform modules for better organization, reusability, and maintainability.

## 📁 Directory Structure

```
modular-version/
├── main.tf                 # Orchestrates all modules
├── variables.tf            # Root-level variables
├── outputs.tf              # Root-level outputs
├── terraform.tfvars        # Your configuration values
│
└── modules/
    ├── networking/         # VPC, subnets, security groups, VPC endpoints
    ├── storage/            # S3 buckets for workspace and Unity Catalog
    ├── iam/                # IAM roles and policies
    ├── kms/                # Optional KMS encryption keys
    ├── unity_catalog/      # Unity Catalog metastore, catalogs, grants
    └── databricks_workspace/ # Workspace creation and configuration
```

## 🚀 Quick Start

### 1. Prerequisites

- Terraform >= 1.0
- AWS CLI configured with appropriate credentials
- Databricks account with service principal (client ID and secret)

### 2. AWS Authentication Setup

You have two options for AWS authentication:

**Option A: Named AWS Profile** (recommended for local development)
```bash
# Configure AWS CLI with your profile
aws configure --profile your-profile-name

# Set profile in terraform.tfvars
aws_profile = "your-profile-name"
```

**Option B: Default Credentials or Environment Variables**
```bash
# Use AWS CLI default credentials
aws configure

# OR use AWS SSO
aws sso login

# OR set environment variables
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
export AWS_SESSION_TOKEN="your-token"  # if using temporary credentials

# Then comment out 'profile' line in main.tf provider block
# or leave aws_profile empty in terraform.tfvars
```

### 3. Configure Variables

Edit `terraform.tfvars` with your values:

```hcl
# Databricks Account Configuration
client_id             = "your-service-principal-id"
client_secret         = "your-service-principal-secret"
databricks_account_id = "your-databricks-account-id"

# AWS Configuration
aws_account_id = "your-aws-account-id"
aws_profile    = "your-aws-profile"  # Use named profile (Option A)
# aws_profile  = ""                  # Leave empty for default credentials (Option B)

# Workspace Configuration
workspace_name        = "my-workspace"
workspace_admin_email = "admin@company.com"
prefix                = "dbx"
region                = "us-west-2"

# Network Configuration
vpc_cidr                 = "10.0.0.0/16"
private_subnet_cidrs     = ["10.0.1.0/24", "10.0.2.0/24"]
privatelink_subnet_cidrs = ["10.0.3.0/24", "10.0.4.0/24"]
public_subnet_cidrs      = ["10.0.101.0/24", "10.0.102.0/24"]
availability_zones       = ["us-west-2a", "us-west-2b"]

# S3 Bucket Names (must be globally unique)
root_storage_bucket_name                = "my-root"
unity_catalog_bucket_name               = "my-uc-metastore"
unity_catalog_external_bucket_name      = "my-uc-external"
unity_catalog_root_storage_bucket_name  = "my-uc-root-storage"

# Optional Features
enable_encryption        = false
create_workspace_catalog = true
```

### 4. Initialize Terraform

```bash
cd modular-version
terraform init
```

### 5. Plan Deployment

```bash
terraform plan
```

### 6. Deploy

```bash
terraform apply
```

**⏰ Important:** After deployment, wait 20 minutes for backend Private Link to stabilize before creating clusters.

## 📦 Modules Overview

### 1. Networking Module

Creates AWS networking infrastructure:
- VPC with DNS support
- Public, private, and PrivateLink subnets
- NAT Gateways for high availability
- Security groups for workspace and VPC endpoints
- VPC endpoints (Workspace, Relay, S3, STS, Kinesis)

### 2. Storage Module

Creates S3 buckets:
- **Root Storage**: Workspace DBFS storage
- **UC Metastore**: Unity Catalog metastore metadata
- **UC Root Storage**: Workspace catalog primary storage
- **UC External**: External data location

All buckets have:
- Versioning enabled
- Public access blocked
- Optional KMS encryption
- Force destroy enabled for cleanup

### 3. IAM Module

Creates IAM roles and policies:
- **Cross-Account Role**: For Databricks control plane
- **UC Metastore Role**: For Unity Catalog access
- **Instance Profile**: For Databricks cluster compute

### 4. KMS Module (Optional)

Creates encryption keys when `enable_encryption = true`:
- Customer-managed KMS key
- Key rotation enabled
- Proper policies for Databricks and S3

### 5. Unity Catalog Module

Creates Unity Catalog resources:
- Metastore (account-level)
- Storage credentials (with dynamic external_id)
- IAM roles and policies (generated via Databricks data sources)
- External locations
- Workspace catalog
- Grants and permissions

### 6. Databricks Workspace Module

Creates the Databricks workspace:
- MWS credentials
- MWS storage configuration
- MWS network configuration
- Private access settings
- Workspace creation
- Workspace admin assignment

## 🔄 Module Dependencies

```
Networking ─┐
            ├─→ Workspace ─→ Unity Catalog
Storage ────┤
            │
IAM ────────┤
            │
KMS ────────┘
```

## 📝 Outputs

After deployment, Terraform provides:

- VPC and networking details
- S3 bucket names
- IAM role ARNs
- Workspace ID and URL
- Unity Catalog metastore and catalog information
- Deployment summary with next steps

View outputs:
```bash
terraform output
```

## 🔧 Customization

### Enable KMS Encryption

```hcl
enable_encryption = true
```

### Disable Workspace Catalog Creation

```hcl
create_workspace_catalog = false
```

### Modify Network CIDR Blocks

Edit the CIDR blocks in `terraform.tfvars` to match your requirements.

## 🧹 Clean Destruction

To cleanly destroy all resources:

1. Set workspace catalog to false:
   ```hcl
   create_workspace_catalog = false
   ```

2. Apply the change:
   ```bash
   terraform apply
   ```

3. Destroy all resources:
   ```bash
   terraform destroy
   ```

## 🆚 vs. Root Version

| Aspect | Modular Version | Root Version |
|--------|----------------|--------------|
| Organization | 6 modules, ~30 files | Single directory, ~15 files |
| Readability | ✅ Excellent | Good |
| Reusability | ✅ High | Limited |
| Maintenance | ✅ Easy | Moderate |
| Complexity | Moderate | Simple |

## 📚 Module Documentation

Each module has its own README with:
- Detailed resource descriptions
- Usage examples
- Input variables
- Output values
- Architecture diagrams

See `modules/*/README.md` for module-specific documentation.

## 🔐 Security Best Practices

✅ All S3 buckets have public access blocked
✅ VPC endpoints for private connectivity
✅ Security groups follow least-privilege principle
✅ IAM roles use Databricks-generated policies
✅ Optional KMS encryption for data at rest
✅ Unity Catalog for data governance

## 🐛 Troubleshooting

### Issue: Terraform can't find modules

**Solution:** Run `terraform init` to download modules.

### Issue: Workspace not accessible

**Solution:** Wait 20 minutes after deployment for Private Link stabilization.

### Issue: Unity Catalog permissions error

**Solution:** Verify workspace admin email is correct and service principal has account admin role.

## 📞 Support

For issues or questions:
1. Check module READMEs for specific module documentation
2. Review Databricks documentation: https://docs.databricks.com
3. Check Terraform AWS provider docs: https://registry.terraform.io/providers/hashicorp/aws

## 🎯 Next Steps

After successful deployment:

1. ✅ Wait 20 minutes for stabilization
2. ✅ Access workspace URL from outputs
3. ✅ Log in with workspace admin email
4. ✅ Verify Unity Catalog catalog is available
5. ✅ Create your first cluster
6. ✅ Start building!

---

**Note:** This modular version provides the same functionality as the root version but with better organization and maintainability.

