***REMOVED*** 🚀 How to Use the Modular Version

This guide walks you through deploying AWS Databricks with Private Link using the modular Terraform configuration.

***REMOVED******REMOVED*** 📋 Prerequisites

Before starting, ensure you have:

- [x] Terraform >= 1.0 installed
- [x] AWS CLI configured
- [x] AWS account with appropriate permissions
- [x] Databricks account
- [x] Databricks service principal (OAuth credentials)

***REMOVED******REMOVED*** 🛠️ Step 1: Prepare Your Environment

***REMOVED******REMOVED******REMOVED*** 1.1 Clone or Navigate to the Directory

```bash
cd /path/to/aws-databricks-privatelink/modular-version
```

***REMOVED******REMOVED******REMOVED*** 1.2 Set Up AWS Credentials

Option A: Using AWS Profile
```bash
export AWS_PROFILE=your-profile-name
```

Option B: Using AWS SSO
```bash
aws sso login --profile your-profile-name
```

Option C: Using AWS Access Keys (not recommended for production)
```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-west-2"
```

***REMOVED******REMOVED******REMOVED*** 1.3 Get Databricks Credentials

You need a Databricks service principal with account admin privileges:

1. Log in to https://accounts.cloud.databricks.com
2. Go to "User Management" → "Service Principals"
3. Create a new service principal or use existing
4. Generate OAuth secret
5. Save the `Client ID` and `Client Secret`

***REMOVED******REMOVED*** ⚙️ Step 2: Configure Variables

***REMOVED******REMOVED******REMOVED*** 2.1 Copy and Edit terraform.tfvars

```bash
cp terraform.tfvars terraform.tfvars.backup
vi terraform.tfvars
```

***REMOVED******REMOVED******REMOVED*** 2.2 Required Variables

Update these in `terraform.tfvars`:

```hcl
***REMOVED*** ============================================================================
***REMOVED*** Databricks Configuration (REQUIRED)
***REMOVED*** ============================================================================
client_id             = "your-service-principal-client-id"
client_secret         = "your-service-principal-secret"
databricks_account_id = "your-databricks-account-id"

***REMOVED*** ============================================================================
***REMOVED*** AWS Configuration (REQUIRED)
***REMOVED*** ============================================================================
aws_account_id = "123456789012"  ***REMOVED*** Your AWS account ID

***REMOVED*** AWS Authentication - Choose one option:
***REMOVED*** Option A: Named profile (recommended for local development)
aws_profile = "your-profile-name"

***REMOVED*** Option B: Default credentials (comment out aws_profile above)
***REMOVED*** aws_profile = ""
***REMOVED*** Then use: aws configure, aws sso login, or environment variables

***REMOVED*** ============================================================================
***REMOVED*** Workspace Configuration (REQUIRED)
***REMOVED*** ============================================================================
workspace_name        = "my-production-workspace"
workspace_admin_email = "admin@yourcompany.com"  ***REMOVED*** Must exist in Databricks account
prefix                = "dbx"
region                = "us-west-2"

***REMOVED*** ============================================================================
***REMOVED*** Network Configuration (CUSTOMIZE AS NEEDED)
***REMOVED*** ============================================================================
vpc_cidr                 = "10.0.0.0/16"
private_subnet_cidrs     = ["10.0.1.0/24", "10.0.2.0/24"]
privatelink_subnet_cidrs = ["10.0.3.0/24", "10.0.4.0/24"]
public_subnet_cidrs      = ["10.0.101.0/24", "10.0.102.0/24"]
availability_zones       = ["us-west-2a", "us-west-2b"]

***REMOVED*** ============================================================================
***REMOVED*** S3 Bucket Names (MUST BE GLOBALLY UNIQUE)
***REMOVED*** ============================================================================
root_storage_bucket_name                = "mycompany-dbx-root"
unity_catalog_bucket_name               = "mycompany-dbx-uc-metastore"
unity_catalog_external_bucket_name      = "mycompany-dbx-uc-external"
unity_catalog_root_storage_bucket_name  = "mycompany-dbx-uc-root-storage"

***REMOVED*** ============================================================================
***REMOVED*** Optional Features
***REMOVED*** ============================================================================
enable_encryption        = false  ***REMOVED*** Set to true for KMS encryption
create_workspace_catalog = true   ***REMOVED*** Set to false to skip catalog creation
```

***REMOVED******REMOVED*** 🎯 Step 3: Initialize Terraform

Initialize Terraform to download providers and modules:

```bash
terraform init
```

Expected output:
```
Initializing modules...
- networking in modules/networking
- storage in modules/storage
- iam in modules/iam
- kms in modules/kms
- databricks_workspace in modules/databricks_workspace
- unity_catalog in modules/unity_catalog

Initializing provider plugins...
- Finding databricks/databricks versions matching "~> 1.0"...
- Finding hashicorp/aws versions matching "~> 5.0"...

Terraform has been successfully initialized!
```

***REMOVED******REMOVED*** 📝 Step 4: Review the Plan

Preview what Terraform will create:

```bash
terraform plan
```

Review the plan carefully. You should see:
- ~60-70 resources to be created
- VPC and networking resources
- S3 buckets
- IAM roles and policies
- VPC endpoints
- Databricks workspace
- Unity Catalog resources

***REMOVED******REMOVED*** 🚀 Step 5: Deploy

Apply the configuration:

```bash
terraform apply
```

Type `yes` when prompted.

**Expected Duration:** 10-15 minutes

***REMOVED******REMOVED******REMOVED*** What Happens During Deployment

1. **Phase 1 (0-2 min):** Random suffix generation, VPC, subnets, security groups
2. **Phase 2 (2-5 min):** S3 buckets, IAM roles, VPC endpoints
3. **Phase 3 (5-10 min):** Databricks workspace creation
4. **Phase 4 (10-15 min):** Unity Catalog metastore, storage credentials, external locations, catalogs

***REMOVED******REMOVED*** ✅ Step 6: Verify Deployment

***REMOVED******REMOVED******REMOVED*** 6.1 Check Terraform Outputs

```bash
terraform output
```

You should see:
```
workspace_url = "https://dbc-xxxxxxxx-xxxx.cloud.databricks.com"
workspace_id = "1234567890123456"
metastore_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
workspace_catalog_name = "dbx_xxxx_catalog"
```

***REMOVED******REMOVED******REMOVED*** 6.2 View Deployment Summary

```bash
terraform output deployment_summary
```

***REMOVED******REMOVED******REMOVED*** 6.3 Access the Workspace

⏰ **IMPORTANT:** Wait 20 minutes before creating clusters!

1. Get the workspace URL:
   ```bash
   terraform output workspace_url
   ```

2. Open the URL in your browser

3. Log in with your workspace admin email

4. Verify Unity Catalog:
   - Click "Data" in the left sidebar
   - You should see your workspace catalog

***REMOVED******REMOVED*** 🧪 Step 7: Test the Deployment

***REMOVED******REMOVED******REMOVED*** 7.1 Create a Test Cluster

⏰ Wait 20 minutes after deployment before creating clusters!

1. Navigate to "Compute" → "Create Cluster"
2. Configure:
   - Name: "test-cluster"
   - Runtime: Latest LTS
   - Instance type: Default
3. Click "Create Cluster"
4. Wait ~5 minutes for cluster to start

***REMOVED******REMOVED******REMOVED*** 7.2 Test Unity Catalog

1. Create a new notebook
2. Run:
   ```sql
   -- Show catalogs
   SHOW CATALOGS;
   
   -- Use workspace catalog
   USE CATALOG your_catalog_name;
   
   -- Create schema
   CREATE SCHEMA IF NOT EXISTS test_schema;
   
   -- Create table
   CREATE TABLE test_schema.test_table (
     id INT,
     name STRING
   );
   
   -- Insert data
   INSERT INTO test_schema.test_table VALUES (1, 'test');
   
   -- Query
   SELECT * FROM test_schema.test_table;
   ```

***REMOVED******REMOVED*** 🔄 Step 8: Making Changes

***REMOVED******REMOVED******REMOVED*** Add KMS Encryption

1. Edit `terraform.tfvars`:
   ```hcl
   enable_encryption = true
   ```

2. Apply changes:
   ```bash
   terraform apply
   ```

***REMOVED******REMOVED******REMOVED*** Add More Catalogs

Edit `modules/unity_catalog/04-workspace-catalog.tf` to add more catalogs.

***REMOVED******REMOVED*** 🧹 Step 9: Cleanup (Destroy)

To destroy all resources:

***REMOVED******REMOVED******REMOVED*** 9.1 Clean Destroy (Recommended)

```bash
***REMOVED*** Step 1: Disable workspace catalog creation
***REMOVED*** Edit terraform.tfvars:
***REMOVED*** create_workspace_catalog = false

terraform apply

***REMOVED*** Step 2: Destroy all resources
terraform destroy
```

***REMOVED******REMOVED******REMOVED*** 9.2 Force Destroy

```bash
terraform destroy
```

⚠️ **Note:** S3 buckets have `force_destroy = true` enabled, so they will be deleted even if they contain data.

***REMOVED******REMOVED*** 🐛 Troubleshooting

***REMOVED******REMOVED******REMOVED*** Issue: "No valid credential sources found"

**Solution:**
```bash
aws sso login --profile your-profile-name
```

***REMOVED******REMOVED******REMOVED*** Issue: "Bucket name already exists"

**Solution:** S3 bucket names must be globally unique. Update bucket names in `terraform.tfvars`.

***REMOVED******REMOVED******REMOVED*** Issue: "Provider configuration not present"

**Solution:**
```bash
terraform init
```

***REMOVED******REMOVED******REMOVED*** Issue: Workspace not accessible

**Solution:** Wait 20 minutes for Private Link stabilization.

***REMOVED******REMOVED******REMOVED*** Issue: "User does not have CREATE EXTERNAL LOCATION"

**Solution:** Verify:
1. Service principal has account admin role
2. Workspace admin email is correct
3. Metastore owner is set correctly

***REMOVED******REMOVED*** 📊 Understanding the Module Structure

```
modular-version/
├── main.tf                      ***REMOVED*** Orchestrates all modules
├── variables.tf                 ***REMOVED*** Root variables
├── outputs.tf                   ***REMOVED*** Root outputs
├── terraform.tfvars             ***REMOVED*** Your values
│
└── modules/
    ├── networking/              ***REMOVED*** VPC, subnets, SGs, VPC endpoints
    │   ├── main.tf
    │   ├── security_groups.tf
    │   ├── vpc_endpoints.tf
    │   └── ...
    │
    ├── storage/                 ***REMOVED*** S3 buckets
    │   └── main.tf
    │
    ├── iam/                     ***REMOVED*** IAM roles and policies
    │   ├── cross_account.tf
    │   ├── unity_catalog.tf
    │   └── instance_profile.tf
    │
    ├── kms/                     ***REMOVED*** Encryption keys
    │   └── main.tf
    │
    ├── databricks_workspace/    ***REMOVED*** Workspace creation
    │   └── main.tf
    │
    └── unity_catalog/           ***REMOVED*** UC metastore, catalogs, grants
        ├── 01-metastore.tf
        ├── 02-root-storage.tf
        ├── 03-external-storage.tf
        ├── 04-workspace-catalog.tf
        └── 05-grants.tf
```

***REMOVED******REMOVED*** 🎓 Next Steps

After successful deployment:

1. ✅ Create compute policies
2. ✅ Set up cluster policies
3. ✅ Configure workspace settings
4. ✅ Add more users and groups
5. ✅ Create additional catalogs and schemas
6. ✅ Set up data pipelines

***REMOVED******REMOVED*** 📚 Additional Resources

- [Databricks Documentation](https://docs.databricks.com)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws)
- [Terraform Databricks Provider](https://registry.terraform.io/providers/databricks/databricks)
- [Databricks Security Reference Architecture](https://github.com/databricks/terraform-databricks-sra)

***REMOVED******REMOVED*** 💡 Tips

- Always use `terraform plan` before `terraform apply`
- Keep your `terraform.tfvars` secure (contains secrets)
- Use remote state for production deployments
- Tag all resources consistently
- Document custom changes

---

**Questions or Issues?** Check the module READMEs or Databricks documentation.

