***REMOVED*** Databricks Workspace with Unity Catalog - Terraform Module

Terraform module for creating a Databricks workspace on GCP with complete Unity Catalog governance, compute policies, and SQL warehouses.

***REMOVED******REMOVED*** Features

- Databricks workspace creation with network configuration
- Unity Catalog setup (storage credentials, external locations, catalogs)
- Instance pools (Small, Medium, Large)
- Cluster policies (Job, All-Purpose, Personal, Shared Compute)
- SQL warehouses with serverless support
- Comprehensive permission management
- Workspace status polling to prevent race conditions

***REMOVED******REMOVED*** Usage

```hcl
module "databricks_workspace" {
  source = "./module"

  ***REMOVED*** Phase Control
  expected_workspace_status     = "RUNNING"
  provision_workspace_resources = true

  ***REMOVED*** Databricks Account
  databricks_account_id             = var.databricks_account_id
  databricks_google_service_account = var.databricks_google_service_account

  ***REMOVED*** Regional Configuration
  private_access_settings_id      = var.private_access_settings_id
  dataplane_relay_vpc_endpoint_id = var.dataplane_relay_vpc_endpoint_id
  rest_api_vpc_endpoint_id        = var.rest_api_vpc_endpoint_id
  databricks_metastore_id         = var.databricks_metastore_id

  ***REMOVED*** Workspace
  workspace_name = "my-workspace"
  metastore_id   = "your-metastore-uuid"

  ***REMOVED*** Network
  network_project_id = "network-project"
  vpc_id             = "my-vpc"
  subnet_id          = "my-subnet"

  ***REMOVED*** GCP Project
  gcpprojectid        = "databricks-project"
  google_project_name = "databricks-project"
  google_region       = "us-east4"

  ***REMOVED*** Metadata
  notificationdistlist = "ops@example.com"
  teamname             = "data-platform"
  org                  = "myorg"
  owner                = "owner@example.com"
  environment          = "prod"

  ***REMOVED*** Compute
  node_type     = "e2"
  compute_types = "Small,Medium,Large"

  ***REMOVED*** Permissions
  permissions_group_role_user = "data-users,data-admins"
  cluster_policy_permissions  = "[{\"role\": \"can_use\", \"group\": [\"data-admins\"]}]"
  pool_usage_permissions      = "[{\"role\": \"can_manage\", \"group\": [\"data-admins\"]}]"

  ***REMOVED*** Unity Catalog
  unity_catalog_config = "[{\"name\": \"main\", \"external_bucket\": \"main-bucket\", \"shared\": \"false\"}]"

  ***REMOVED*** SQL Warehouses
  sqlwarehouse_cluster_config = "[{\"name\": \"small-sql\", \"config\": {\"type\": \"small\", \"max_instance\": 2, \"serverless\": \"true\"}, \"permission\": [{\"role\": \"can_use\", \"group\": [\"data-users\"]}]}]"
}
```

***REMOVED******REMOVED*** Requirements

| Name | Version |
|------|---------|
| terraform | >= 1.0 |
| databricks | ~> 1.95.0 |
| google | ~> 6.5.0 |
| null | ~> 3.0 |
| random | ~> 3.0 |

***REMOVED******REMOVED*** Providers

| Name | Version |
|------|---------|
| databricks.accounts | ~> 1.95.0 |
| databricks.workspace | ~> 1.95.0 |
| google.internal | ~> 6.5.0 |
| google.external | ~> 6.5.0 |
| null | ~> 3.0 |
| random | ~> 3.0 |

***REMOVED******REMOVED*** Inputs

***REMOVED******REMOVED******REMOVED*** Required Inputs

| Name | Description | Type |
|------|-------------|------|
| databricks_account_id | Databricks account ID (UUID) | `string` |
| databricks_google_service_account | GCP service account for Databricks authentication | `string` |
| private_access_settings_id | Regional private access settings IDs | `map(string)` |
| dataplane_relay_vpc_endpoint_id | Regional dataplane relay VPC endpoint IDs | `map(string)` |
| rest_api_vpc_endpoint_id | Regional REST API VPC endpoint IDs | `map(string)` |
| databricks_metastore_id | Regional Unity Catalog metastore IDs | `map(string)` |
| workspace_name | Name of the Databricks workspace | `string` |
| metastore_id | Unity Catalog metastore ID to assign | `string` |
| network_project_id | GCP project ID containing the VPC | `string` |
| vpc_id | VPC network name | `string` |
| subnet_id | Subnet name for Databricks nodes | `string` |
| gcpprojectid | GCP project ID for workspace resources | `string` |
| google_project_name | GCP project name for workspace resources | `string` |
| notificationdistlist | Email distribution list for notifications | `string` |
| teamname | Team name for tagging | `string` |
| org | Organization name for tagging | `string` |
| owner | Owner email for tagging | `string` |
| permissions_group_role_user | Comma-separated list of groups for USER role | `string` |
| cluster_policy_permissions | JSON string defining cluster policy permissions | `string` |
| pool_usage_permissions | JSON string defining instance pool permissions | `string` |
| unity_catalog_config | JSON string defining Unity Catalog configuration | `string` |
| sqlwarehouse_cluster_config | JSON string defining SQL warehouse configuration | `string` |

***REMOVED******REMOVED******REMOVED*** Optional Inputs

| Name | Description | Type | Default |
|------|-------------|------|---------|
| expected_workspace_status | Expected workspace status to wait for | `string` | `"PROVISIONING"` |
| provision_workspace_resources | Whether to provision workspace resources | `bool` | `false` |
| google_region | GCP region for workspace | `string` | `"us-east4"` |
| environment | Environment name (dev, staging, prod) | `string` | `"dev"` |
| applicationtier | Application tier for tagging | `string` | `"tier2"` |
| costcenter | Cost center code for billing tracking | `string` | `""` |
| apmid | APM ID for billing tracking | `string` | `""` |
| ssp | SSP code for billing tracking | `string` | `""` |
| trproductid | Product ID for billing tracking | `string` | `""` |
| node_type | GCP machine type family | `string` | `"e2"` |
| compute_types | Comma-separated list of pool sizes | `string` | `"Small,Medium,Large"` |
| permissions_group_role_admin | Comma-separated list of groups for ADMIN role | `string` | `""` |
| permissions_user_role_user | Comma-separated list of users for USER role | `string` | `""` |
| permissions_spn_role_user | Comma-separated list of SPNs for USER role | `string` | `""` |
| permissions_spn_role_admin | Comma-separated list of SPNs for ADMIN role | `string` | `""` |
| external_project | Whether to use external project for GCS buckets | `bool` | `false` |
| bucket_project_id | GCP project ID for external buckets | `string` | `""` |
| unity_catalog_permissions | JSON string defining UC permissions | `string` | `""` |
| external_location_permissions | JSON string defining external location permissions | `string` | `""` |
| storage_credentials_permissions | JSON string defining storage credential permissions | `string` | `""` |
| ext_unity_catalog_config | JSON string for external catalog configuration | `string` | `""` |
| ext_unity_catalog_permissions | JSON string for external catalog permissions | `string` | `""` |
| foriegn_catalog_bq_connection | JSON string for BigQuery catalog connections | `string` | `""` |

***REMOVED******REMOVED*** Outputs

| Name | Description |
|------|-------------|
| workspace_id | Databricks workspace ID |
| workspace_url | Databricks workspace URL |
| workspace_name | Databricks workspace name |
| workspace_gsa_email | Google service account email created for the workspace |
| workspace_status | Current workspace status |
| metastore_id | Unity Catalog metastore ID assigned to workspace |
| storage_credentials | Map of storage credentials created |
| external_locations | Map of external locations created |
| catalogs | Map of Unity Catalog catalogs created |
| instance_pools | Map of instance pools created |
| cluster_policies | Map of cluster policies created |
| sql_warehouses | Map of SQL warehouses created |
| gcs_buckets | Map of GCS buckets created for Unity Catalog |

***REMOVED******REMOVED*** Resources Created

***REMOVED******REMOVED******REMOVED*** Phase 1 (PROVISIONING)
- `databricks_mws_networks.dbx_network` - Network configuration
- `databricks_mws_workspaces.dbx_workspace` - Workspace (shell)

***REMOVED******REMOVED******REMOVED*** Phase 2 (RUNNING)
- `null_resource.wait_for_workspace_running` - Status polling
- `databricks_metastore_assignment.this` - Metastore assignment
- `databricks_mws_permission_assignment.*` - Permission assignments (groups, users, SPNs)
- `databricks_storage_credential.*` - Storage credentials
- `google_storage_bucket.*` - GCS buckets for Unity Catalog
- `google_storage_bucket_iam_member.*` - IAM bindings for buckets
- `databricks_external_location.*` - External locations
- `databricks_catalog.*` - Unity Catalog catalogs
- `databricks_workspace_binding.*` - Catalog workspace bindings
- `databricks_grants.*` - Permission grants
- `databricks_instance_pool.*` - Instance pools (Small, Medium, Large)
- `databricks_cluster_policy.*` - Cluster policies (Job, All-Purpose, Personal, Shared)
- `databricks_permissions.*` - Resource-level permissions
- `databricks_sql_endpoint.*` - SQL warehouses
- `random_string.suffix` - Random suffix for resource naming

***REMOVED******REMOVED*** Workspace Status Polling

The module includes a workspace status polling mechanism that prevents race conditions:

```hcl
resource "null_resource" "wait_for_workspace_running" {
  count = var.provision_workspace_resources && var.expected_workspace_status == "RUNNING" ? 1 : 0

  provisioner "local-exec" {
    command = <<-EOT
      ***REMOVED*** Poll Databricks API every 10 seconds for up to 10 minutes
      ***REMOVED*** Waits for workspace status = "RUNNING"
    EOT
  }
}
```

All workspace resources depend on this check completing successfully.

***REMOVED******REMOVED*** Cluster Policy Structure

Policies are created per compute size with the following types:

***REMOVED******REMOVED******REMOVED*** Job Policies
- Fixed `cluster_type = "job"`
- Autoscaling workers
- DBU limits
- Node type restrictions

***REMOVED******REMOVED******REMOVED*** Job Pool Policies
- Same as Job Policy
- Includes `instance_pool_id` reference

***REMOVED******REMOVED******REMOVED*** All-Purpose Policies
- Interactive workloads
- Auto-termination (60 min)
- Autoscaling workers
- DBU limits

***REMOVED******REMOVED******REMOVED*** All-Purpose Pool Policies
- Same as All-Purpose Policy
- Includes `instance_pool_id` reference

***REMOVED******REMOVED******REMOVED*** Special Policies
- **Personal Compute**: Override for family-based node selection
- **Shared Compute**: Override for shared cluster usage

***REMOVED******REMOVED*** Unity Catalog Configuration

***REMOVED******REMOVED******REMOVED*** Storage Credentials
Created with `ISOLATION_MODE_OPEN` to allow explicit workspace bindings.

***REMOVED******REMOVED******REMOVED*** External Locations
- Point to GCS buckets
- Depend on storage credentials and IAM bindings
- Granted permissions per JSON configuration

***REMOVED******REMOVED******REMOVED*** Catalogs
- Created with storage root pointing to external location
- Explicitly bound to workspace
- Permissions granted to groups (data_editor, data_reader, data_writer)

***REMOVED******REMOVED*** JSON Configuration Format

***REMOVED******REMOVED******REMOVED*** Unity Catalog Config
```json
[
  {
    "name": "catalog_name",
    "external_bucket": "gcs-bucket-name",
    "shared": "false"
  }
]
```

***REMOVED******REMOVED******REMOVED*** SQL Warehouse Config
```json
[
  {
    "name": "warehouse_name",
    "config": {
      "type": "small",
      "max_instance": 2,
      "serverless": "true"
    },
    "permission": [
      {
        "role": "can_use",
        "group": ["group1", "group2"]
      }
    ]
  }
]
```

***REMOVED******REMOVED******REMOVED*** Permission Config
```json
[
  {
    "name": "catalog_name",
    "permission": [
      {
        "role": "data_editor",
        "group": ["admins"]
      },
      {
        "role": "data_reader",
        "group": ["readers"]
      }
    ]
  }
]
```

***REMOVED******REMOVED*** Notes

***REMOVED******REMOVED******REMOVED*** Authentication
The module uses service account impersonation (`google_service_account` parameter). Alternatively, you can use:
- `google_credentials` parameter with path to key file
- `GOOGLE_APPLICATION_CREDENTIALS` environment variable
- Application Default Credentials (ADC)

***REMOVED******REMOVED******REMOVED*** Terraform State
This module creates many resources. Consider:
- Remote state backend (GCS, S3)
- State locking
- Separate state files per environment

***REMOVED******REMOVED******REMOVED*** Permissions Required
The service account needs:
- GCP: `compute.networkAdmin`, `storage.admin`, `iam.serviceAccountUser`
- Databricks: Account admin role

***REMOVED******REMOVED******REMOVED*** Limitations
- Workspace GSA group membership is disabled (requires additional Google Workspace permissions)
- Maximum 10-minute timeout for workspace status polling
- Regional metastore must exist before deployment

***REMOVED******REMOVED*** Example Configurations

See `../example/` for full working example with:
- 2-phase deployment
- Complete variable configuration
- All permission models
- Multiple catalogs and SQL warehouses

***REMOVED******REMOVED*** Related Modules

- `../../../infra4db/` - GCP infrastructure foundation (VPC, subnets, NAT)
- `../../../byovpc-psc-cmek-ws/` - Maximum security workspace (PSC + CMEK)

***REMOVED******REMOVED*** Support

For issues:
- Module bugs: Open issue in repository
- Databricks issues: Contact Databricks support
- GCP issues: Consult GCP documentation
