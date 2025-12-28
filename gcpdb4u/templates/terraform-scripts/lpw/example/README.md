***REMOVED*** Complete Databricks Workspace Deployment Example

This example demonstrates a complete Databricks workspace deployment on GCP with Unity Catalog, compute policies, and SQL warehouses using the 2-phase deployment model.

***REMOVED******REMOVED*** What This Example Creates

***REMOVED******REMOVED******REMOVED*** Phase 1: PROVISIONING
- Databricks workspace (shell configuration)
- Network configuration object
- Workspace GSA (Google Service Account created by Databricks)

***REMOVED******REMOVED******REMOVED*** Phase 2: RUNNING
- **Unity Catalog**: 1 catalog with storage credentials, external locations, and GCS buckets
- **Compute**: 3 instance pools (Small, Medium, Large) and associated cluster policies
- **SQL Analytics**: 3 SQL warehouses (Small, Medium, Large) with serverless support
- **Permissions**: Workspace-level and resource-level permissions for specified groups

***REMOVED******REMOVED*** Prerequisites

***REMOVED******REMOVED******REMOVED*** 1. Databricks Account Setup
- Access to Databricks account console: https://accounts.gcp.databricks.com/
- Account admin role
- Regional Unity Catalog metastore created
- Databricks groups created (e.g., `databricks-admins`, `databricks-writers`, `databricks-readers`)

***REMOVED******REMOVED******REMOVED*** 2. GCP Environment
- GCP project for Databricks workspace
- Shared VPC network configured
- Subnet allocated for Databricks (minimum /26 CIDR)
- Service account with permissions:
  - `roles/compute.networkAdmin`
  - `roles/storage.admin`
  - `roles/iam.serviceAccountUser`
  - Databricks account admin

***REMOVED******REMOVED******REMOVED*** 3. Regional Infrastructure IDs
Contact your Databricks account team to obtain:
- Databricks account ID (UUID)
- Private access settings IDs (per region)
- Dataplane relay VPC endpoint IDs (per region)
- REST API VPC endpoint IDs (per region)
- Unity Catalog metastore IDs (per region)

***REMOVED******REMOVED******REMOVED*** 4. Tools
- Terraform >= 1.0
- gcloud CLI (for authentication)
- Access to GCP project

***REMOVED******REMOVED*** Directory Structure

```
complete/
├── README.md                    ***REMOVED*** This file
├── main.tf                      ***REMOVED*** Module invocation with all parameters
├── variables.tf                 ***REMOVED*** Variable definitions (comprehensive)
├── locals.tf                    ***REMOVED*** Phase configuration logic
├── outputs.tf                   ***REMOVED*** Output forwarding from module
└── terraform.tfvars.example     ***REMOVED*** Configuration template with comments
```

***REMOVED******REMOVED*** Step-by-Step Deployment Guide

***REMOVED******REMOVED******REMOVED*** Step 1: Prepare Configuration

***REMOVED******REMOVED******REMOVED******REMOVED*** 1.1 Copy Example Configuration
```bash
cd examples/complete/
cp terraform.tfvars.example terraform.tfvars
```

***REMOVED******REMOVED******REMOVED******REMOVED*** 1.2 Edit terraform.tfvars
```bash
***REMOVED*** Use your preferred editor
vim terraform.tfvars
***REMOVED*** or
code terraform.tfvars
```

***REMOVED******REMOVED******REMOVED******REMOVED*** 1.3 Critical Values to Configure

**Databricks Account** (from your account team):
```hcl
databricks_account_id = "YOUR-ACCOUNT-UUID"

private_access_settings_id = {
  "us-east4" = "YOUR-PRIVATE-ACCESS-SETTINGS-UUID"
}

dataplane_relay_vpc_endpoint_id = {
  "us-east4" = "YOUR-DATAPLANE-RELAY-UUID"
}

rest_api_vpc_endpoint_id = {
  "us-east4" = "YOUR-REST-API-UUID"
}

databricks_metastore_id = {
  "us-east4" = "YOUR-METASTORE-UUID"
}

metastore_id = "YOUR-METASTORE-UUID"  ***REMOVED*** Same as above for your region
```

**Service Account**:
```hcl
databricks_google_service_account = "terraform-sa@your-project.iam.gserviceaccount.com"
```

**Network Configuration**:
```hcl
network_project_id = "your-network-project-id"
vpc_id             = "your-vpc-name"
subnet_id          = "your-subnet-name"
```

**GCP Project**:
```hcl
gcpprojectid        = "your-databricks-project"
google_project_name = "your-databricks-project"
google_region       = "us-east4"
```

**Workspace Details**:
```hcl
workspace_name       = "my-databricks-workspace"
notificationdistlist = "ops-team@example.com"
teamname             = "data-platform"
org                  = "myorganization"
owner                = "platform-owner@example.com"
environment          = "dev"  ***REMOVED*** or prod, staging
```

**Databricks Groups** (must exist in your account):
```hcl
permissions_group_role_user = "databricks-readers,databricks-writers,databricks-admins"
```

**Unity Catalog**:
```hcl
unity_catalog_config = "[{\"name\": \"my_catalog\", \"external_bucket\": \"my-catalog-bucket\", \"shared\": \"false\"}]"
```

***REMOVED******REMOVED******REMOVED*** Step 2: Authenticate with GCP

```bash
***REMOVED*** Option 1: Use gcloud ADC (for local development)
gcloud auth application-default login

***REMOVED*** Option 2: Service account impersonation (recommended)
gcloud auth application-default login --impersonate-service-account=terraform-sa@project.iam.gserviceaccount.com

***REMOVED*** Verify authentication
gcloud auth application-default print-access-token
```

***REMOVED******REMOVED******REMOVED*** Step 3: Initialize Terraform

```bash
terraform init
```

Expected output:
```
Initializing modules...
Initializing the backend...
Initializing provider plugins...
- databricks/databricks v1.95.0
- hashicorp/google v6.5.0
- hashicorp/null v3.0.0
- hashicorp/random v3.0.0

Terraform has been successfully initialized!
```

***REMOVED******REMOVED******REMOVED*** Step 4: Phase 1 - PROVISIONING

***REMOVED******REMOVED******REMOVED******REMOVED*** 4.1 Plan Phase 1
```bash
terraform plan -var="phase=PROVISIONING"
```

Review the plan. It should show:
- 1 network configuration to be created
- 1 workspace to be created
- 0 workspace resources (pools, policies, UC)

***REMOVED******REMOVED******REMOVED******REMOVED*** 4.2 Apply Phase 1
```bash
terraform apply -var="phase=PROVISIONING"
```

Type `yes` when prompted.

Expected duration: 2-5 minutes

***REMOVED******REMOVED******REMOVED******REMOVED*** 4.3 Note Outputs
```bash
terraform output workspace_gsa_email
```

Example output:
```
"db-1234567890123456@prod-gcp-us-east4.iam.gserviceaccount.com"
```

**SAVE THIS EMAIL** - you'll need it for the manual step.

***REMOVED******REMOVED******REMOVED*** Step 5: Manual Action - Add Workspace GSA to Operator Group

⚠️ **CRITICAL**: The workspace GSA must be added to your operator group before proceeding to Phase 2.

***REMOVED******REMOVED******REMOVED******REMOVED*** Option A: Google Workspace (if using workspace directory)
1. Go to admin.google.com
2. Navigate to Groups
3. Find your operator group (e.g., `lpw-ws-operator@example.com`)
4. Add the workspace GSA as a member
5. Wait 5-10 minutes for propagation

***REMOVED******REMOVED******REMOVED******REMOVED*** Option B: GCP IAM (alternative)
1. Add the workspace GSA to a GCP IAM binding on required resources
2. Grant necessary permissions for workspace operation

***REMOVED******REMOVED******REMOVED*** Step 6: Verify Workspace Status

Before proceeding to Phase 2, verify the workspace is in RUNNING state:

```bash
***REMOVED*** Check in Databricks console
open $(terraform output -raw workspace_url)

***REMOVED*** Or check via gcloud (requires access)
gcloud alpha databricks workspaces describe WORKSPACE_ID --region=us-east4
```

Wait until status shows `RUNNING` (typically 10-20 minutes after Phase 1).

***REMOVED******REMOVED******REMOVED*** Step 7: Phase 2 - RUNNING

***REMOVED******REMOVED******REMOVED******REMOVED*** 7.1 Plan Phase 2
```bash
terraform plan -var="phase=RUNNING"
```

Review the plan. It should show many resources to be created:
- Metastore assignment
- Storage credentials
- GCS buckets + IAM bindings
- External locations
- Catalogs
- Instance pools (3)
- Cluster policies (multiple per pool size)
- SQL warehouses (3)
- Permission grants

***REMOVED******REMOVED******REMOVED******REMOVED*** 7.2 Apply Phase 2
```bash
terraform apply -var="phase=RUNNING"
```

Type `yes` when prompted.

Expected duration: 10-15 minutes

The module will:
1. Attach network to workspace
2. Poll workspace status (waits for RUNNING)
3. Assign metastore
4. Create all Unity Catalog resources
5. Create compute resources
6. Create SQL warehouses
7. Grant all permissions

***REMOVED******REMOVED******REMOVED******REMOVED*** 7.3 Monitor Progress
```bash
***REMOVED*** In another terminal, watch the status
watch -n 5 'terraform show | grep status'
```

***REMOVED******REMOVED******REMOVED*** Step 8: Verify Deployment

***REMOVED******REMOVED******REMOVED******REMOVED*** 8.1 Check Outputs
```bash
terraform output
```

Important outputs:
- `workspace_url` - Access your workspace
- `workspace_id` - Workspace identifier
- `catalogs` - Unity Catalog names
- `instance_pools` - Pool IDs
- `sql_warehouses` - SQL warehouse IDs

***REMOVED******REMOVED******REMOVED******REMOVED*** 8.2 Verify in Databricks UI
```bash
***REMOVED*** Open workspace
open $(terraform output -raw workspace_url)
```

**Check**:
- Unity Catalog → Catalogs → Your catalog exists
- Compute → Instance Pools → 3 pools (Small, Medium, Large)
- SQL Warehouses → 3 warehouses
- Settings → Compute Policies → Multiple policies exist

***REMOVED******REMOVED******REMOVED******REMOVED*** 8.3 Test Permissions
Log in as a user from your configured groups and verify:
- Can access workspace
- Can see catalogs based on granted permissions
- Can use SQL warehouses
- Can create clusters using policies

***REMOVED******REMOVED*** Configuration Customization

***REMOVED******REMOVED******REMOVED*** Add More Catalogs
```hcl
unity_catalog_config = "[
  {\"name\": \"prod_data\", \"external_bucket\": \"prod-bucket\", \"shared\": \"false\"},
  {\"name\": \"dev_data\", \"external_bucket\": \"dev-bucket\", \"shared\": \"false\"}
]"

unity_catalog_permissions = "[
  {\"name\": \"prod_data\", \"permission\": [...]},
  {\"name\": \"dev_data\", \"permission\": [...]}
]"
```

***REMOVED******REMOVED******REMOVED*** Customize SQL Warehouses
```hcl
sqlwarehouse_cluster_config = "[
  {\"name\": \"tiny-sql\", \"config\": {\"type\": \"x-small\", \"max_instance\": 1, \"serverless\": \"true\"}, \"permission\": [...]},
  {\"name\": \"huge-sql\", \"config\": {\"type\": \"2x-large\", \"max_instance\": 10, \"serverless\": \"true\"}, \"permission\": [...]}
]"
```

***REMOVED******REMOVED******REMOVED*** Modify Compute Types
```hcl
compute_types = "Medium,Large"  ***REMOVED*** Only create Medium and Large pools
```

***REMOVED******REMOVED******REMOVED*** Add Billing Tags
```hcl
costcenter  = "CC12345"
apmid       = "APM000000"
ssp         = "SSP000000"
trproductid = "0000"
```

***REMOVED******REMOVED*** Troubleshooting

***REMOVED******REMOVED******REMOVED*** Issue: terraform init fails
**Error**: `Could not download module`
**Solution**:
```bash
***REMOVED*** Verify module path is correct
ls -la ../../modules/workspace-with-uc/

***REMOVED*** Re-initialize
rm -rf .terraform .terraform.lock.hcl
terraform init
```

***REMOVED******REMOVED******REMOVED*** Issue: Phase 1 fails with network error
**Error**: `Error creating network: VPC not found`
**Solution**:
- Verify `network_project_id`, `vpc_id`, and `subnet_id` are correct
- Check service account has `compute.networkViewer` role
- Ensure VPC is in the same region as workspace

***REMOVED******REMOVED******REMOVED*** Issue: Workspace stuck in PROVISIONING
**Symptoms**: Phase 2 hangs waiting for RUNNING status
**Solution**:
- Check workspace status in Databricks console
- Verify no quota issues in GCP project
- Check GCP audit logs for errors
- Contact Databricks support if stuck > 30 minutes

***REMOVED******REMOVED******REMOVED*** Issue: Permission denied creating storage credentials
**Error**: `Error: insufficient permissions`
**Solution**:
- Verify workspace GSA was added to operator group
- Wait 10-15 minutes after adding GSA
- Check that service account has Databricks account admin role

***REMOVED******REMOVED******REMOVED*** Issue: GCS bucket already exists
**Error**: `Error creating bucket: bucket already exists`
**Solution**:
```bash
***REMOVED*** Remove bucket from state (if safe)
terraform state rm 'module.local_databricks.google_storage_bucket.internal_buckets["catalog_name"]'

***REMOVED*** Or rename in configuration
unity_catalog_config = "[{\"name\": \"catalog_name\", \"external_bucket\": \"new-unique-bucket-name\", ...}]"
```

***REMOVED******REMOVED******REMOVED*** Issue: Group not found
**Error**: `Error: group not found in account`
**Solution**:
- Create groups in Databricks account console first
- Group names are case-sensitive
- Verify spelling matches exactly

***REMOVED******REMOVED*** Updating the Deployment

***REMOVED******REMOVED******REMOVED*** Update Workspace Resources
```bash
***REMOVED*** Modify terraform.tfvars
vim terraform.tfvars

***REMOVED*** Plan changes
terraform plan -var="phase=RUNNING"

***REMOVED*** Apply changes
terraform apply -var="phase=RUNNING"
```

***REMOVED******REMOVED******REMOVED*** Add Users to Groups
Done in Databricks account console - no Terraform changes needed.

***REMOVED******REMOVED******REMOVED*** Scale Compute
```bash
***REMOVED*** Edit locals.tf to increase pool max_capacity
vim ../../modules/workspace-with-uc/locals.tf

***REMOVED*** Apply changes
terraform apply -var="phase=RUNNING"
```

***REMOVED******REMOVED*** Destroying Resources

⚠️ **WARNING**: This will delete the workspace and all data!

```bash
***REMOVED*** Destroy workspace resources first (Phase 2)
terraform destroy -var="phase=RUNNING"

***REMOVED*** Then destroy workspace shell (Phase 1)
terraform destroy -var="phase=PROVISIONING"
```

**Note**: Some resources may require manual cleanup:
- GCS buckets (if not empty)
- Service accounts created by Databricks
- IAM bindings

***REMOVED******REMOVED*** Cost Considerations

This example creates billable resources:

**GCP Costs**:
- GCS buckets (storage)
- VPC networking (if not using existing)

**Databricks Costs**:
- Workspace compute (DBUs)
- SQL warehouse usage (DBUs)
- Storage in DBFS

**Cost Optimization**:
- Use spot instances in cluster policies
- Set auto-termination timeouts
- Right-size SQL warehouses for workload
- Delete unused resources

***REMOVED******REMOVED*** Next Steps

After successful deployment:

1. **Configure Data Sources**: Connect to your data lakes, databases
2. **Create Notebooks**: Start building data pipelines
3. **Set Up CI/CD**: Automate deployments with GitHub Actions/GitLab CI
4. **Enable Monitoring**: Configure log analytics and alerts
5. **Security Hardening**: Review and restrict permissions as needed
6. **Train Users**: Onboard data teams to the new workspace

***REMOVED******REMOVED*** Additional Resources

- [Main Module Documentation](../../README.md)
- [Module Reference](../../modules/workspace-with-uc/README.md)
- [Databricks on GCP Docs](https://docs.gcp.databricks.com/)
- [Unity Catalog Guide](https://docs.databricks.com/data-governance/unity-catalog/)
- [Terraform Databricks Provider](https://registry.terraform.io/providers/databricks/databricks/)

***REMOVED******REMOVED*** Getting Help

- **Module Issues**: Open an issue in the repository
- **Databricks Support**: Contact your Databricks account team
- **GCP Issues**: Consult GCP support or documentation

---

**Last Updated**: 2025-12-28
