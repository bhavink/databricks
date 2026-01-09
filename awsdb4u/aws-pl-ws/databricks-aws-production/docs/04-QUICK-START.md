***REMOVED*** 04 - Quick Start (5 Minutes)

> **Deploy Fast**: Minimal steps to get your workspace running.

```
⏱️ 5 minutes setup + 15 minutes deployment = 20 minutes total
```

---

***REMOVED******REMOVED*** Prerequisites Complete?

✅ [00-PREREQUISITES.md](00-PREREQUISITES.md) - System configured  
✅ `TF_VAR_*` environment variables set  
✅ AWS credentials working  

**Not ready?** → [00-PREREQUISITES.md](00-PREREQUISITES.md)

---

***REMOVED******REMOVED*** Step 1: Create Configuration File (2 minutes)

***REMOVED******REMOVED******REMOVED*** 1.1 Copy Example Configuration

```bash
***REMOVED*** Navigate to project directory
cd databricks-aws-production

***REMOVED*** Copy example file to create your configuration
cp terraform.tfvars.example terraform.tfvars
```

**Important**: `terraform.tfvars` is git-ignored for security (never commit credentials!)

***REMOVED******REMOVED******REMOVED*** 1.2 Edit Configuration

Open `terraform.tfvars` and update these values:

```hcl
***REMOVED*** ============================================================================
***REMOVED*** REQUIRED: Change These Values
***REMOVED*** ============================================================================

***REMOVED*** Workspace
workspace_name = "my-prod-workspace"
prefix         = "dbx"
region         = "us-west-1"

***REMOVED*** S3 Buckets (must be globally unique!)
root_storage_bucket_name               = "mycompany-dbx-root-storage"
unity_catalog_bucket_name              = "mycompany-dbx-uc-metastore"
unity_catalog_root_storage_bucket_name = "mycompany-dbx-uc-root-storage"
unity_catalog_external_bucket_name     = "mycompany-dbx-uc-external"

***REMOVED*** Unity Catalog
workspace_catalog_name = "prod"

***REMOVED*** ============================================================================
***REMOVED*** OPTIONAL: Review & Adjust
***REMOVED*** ============================================================================

***REMOVED*** Network (defaults are production-ready)
vpc_cidr                 = "10.0.0.0/22"
private_subnet_cidrs     = ["10.0.1.0/24", "10.0.2.0/24"]
privatelink_subnet_cidrs = ["10.0.3.0/26", "10.0.3.64/26"]
public_subnet_cidrs      = ["10.0.0.0/26", "10.0.0.64/26"]

***REMOVED*** Security
enable_private_link  = true   ***REMOVED*** Private Link (recommended for production)
enable_encryption    = true   ***REMOVED*** S3 KMS encryption
enable_workspace_cmk = false  ***REMOVED*** Workspace CMK (DBFS/EBS/MS) - set to true for full encryption
```

**Note**: Credentials are set via environment variables (see Prerequisites)  
**Tip**: Random suffix auto-added to bucket names (avoids conflicts)

---

***REMOVED******REMOVED*** Step 2: Deploy (3 minutes)

```bash
***REMOVED*** Initialize Terraform (first time only)
terraform init

***REMOVED*** Review what will be created (optional but recommended)
terraform plan

***REMOVED*** Deploy everything
terraform apply
***REMOVED*** Review the plan, then type: yes
```

⏱️ **Wait**: 15-20 minutes for deployment

---

***REMOVED******REMOVED*** Step 3: Get Workspace URL

```bash
***REMOVED*** View deployment summary
terraform output deployment_summary

***REMOVED*** Or just the URL
terraform output workspace_url
```

---

***REMOVED******REMOVED*** Step 4: Access Workspace

1. **Open workspace URL** from output
2. **Log in** with your Databricks account credentials
3. **⏰ WAIT 20 MINUTES** before creating clusters (Private Link DNS propagation)

**Tip**: Bookmark the workspace URL for easy access

---

***REMOVED******REMOVED*** Common Customizations

***REMOVED******REMOVED******REMOVED*** Disable Private Link (Lowest Cost)

```hcl
enable_private_link = false
```

***REMOVED******REMOVED******REMOVED*** Enable S3 Encryption

```hcl
enable_encryption = true
```

***REMOVED******REMOVED******REMOVED*** Enable Full CMK Encryption

```hcl
enable_encryption    = true  ***REMOVED*** S3 buckets
enable_workspace_cmk = true  ***REMOVED*** DBFS/EBS/MS
```

***REMOVED******REMOVED******REMOVED*** Different Region

```hcl
region = "us-east-1"
```

VPC endpoint service names auto-detected ✅

---

***REMOVED******REMOVED*** What Gets Created?

```
65-70 Resources:
├── VPC + 3 subnet tiers (public/private/privatelink)
├── NAT Gateways (2 AZs)
├── Security Groups (2)
├── VPC Endpoints (5: Databricks x2, AWS services x3)
├── S3 Buckets (4: DBFS, UC metastore, UC external, UC root)
├── IAM Roles (4: Cross-account, UC metastore, UC external, instance profile)
├── KMS Keys (2: S3 encryption, Workspace CMK) [optional]
├── Databricks Workspace
├── Unity Catalog (metastore, catalog, external location)
└── Workspace Admin Assignment
```

**Details**: [01-ARCHITECTURE.md](01-ARCHITECTURE.md)

---

***REMOVED******REMOVED*** Clean Up

```bash
terraform destroy
***REMOVED*** Type: yes
```

**Issues?** See [05-TROUBLESHOOTING.md](05-TROUBLESHOOTING.md***REMOVED***destroy-issues)

---

***REMOVED******REMOVED*** Next Steps

✅ **Understand architecture** → [01-ARCHITECTURE.md](01-ARCHITECTURE.md)  
✅ **Learn IAM roles** → [02-IAM-SECURITY.md](02-IAM-SECURITY.md)  
✅ **Review network/security** → [03-NETWORK-ENCRYPTION.md](03-NETWORK-ENCRYPTION.md)  
✅ **Troubleshooting** → [05-TROUBLESHOOTING.md](05-TROUBLESHOOTING.md)

---

***REMOVED******REMOVED*** Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| Bucket already exists | Change bucket names in terraform.tfvars |
| AWS auth error | `aws sso login --profile your-profile` |
| Can't access workspace | Wait 20 minutes after deployment |
| Provider errors | Run `terraform init` |
| Terraform not found | Install: [Prerequisites](00-PREREQUISITES.md***REMOVED***31-install-terraform) |

**More Help**: [05-TROUBLESHOOTING.md](05-TROUBLESHOOTING.md)

**Databricks Docs**: [Getting Started](https://docs.databricks.com/aws/en/getting-started/index.html)
