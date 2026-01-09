# Unity Catalog Module

This module provisions Unity Catalog resources for Databricks, including metastore, storage credentials, external locations, and workspace catalog.

## Architecture

This module follows the Databricks Security Reference Architecture (SRA) pattern for Unity Catalog setup:

1. **Metastore Creation** (Account-level, independent)
2. **Metastore Assignment** (Links metastore to workspace)
3. **Storage Credentials** (Creates credentials with dynamic external_id)
4. **IAM Roles & Policies** (Generated using Databricks data sources)
5. **External Locations** (Registers S3 buckets as Unity Catalog locations)
6. **Workspace Catalog** (Creates catalog using root storage)
7. **Grants** (Assigns permissions to workspace admin and users)

## Resources Created

### Account-Level
- Unity Catalog Metastore
- Metastore assignment to workspace

### Workspace-Level
- **Root Storage**: Credential, IAM role/policy, external location
- **External Storage**: Credential, IAM role/policy, external location
- Workspace catalog (using root storage)
- Default namespace setting
- Grants and permissions

## Key Features

- ✅ Follows SRA best practices
- ✅ Dynamic external_id generation
- ✅ 30-second IAM propagation wait
- ✅ Conditional resource creation
- ✅ Proper dependency management
- ✅ Clean destroy capability

## Usage

```hcl
module "unity_catalog" {
  source = "./modules/unity_catalog"
  
  prefix                              = "dbx-abc123"
  region                              = "us-west-2"
  workspace_name                      = "my-workspace"
  workspace_id                        = "1234567890123456"
  workspace_admin_email               = "admin@company.com"
  client_id                           = "service-principal-id"
  client_secret                       = "service-principal-secret"
  aws_account_id                      = "123456789012"
  databricks_account_id               = "account-id"
  create_workspace_catalog            = true
  unity_catalog_root_storage_bucket   = "my-uc-root-storage"
  unity_catalog_external_bucket       = "my-uc-external"
  
  tags = {
    Environment = "Production"
  }
  
  providers = {
    databricks.account   = databricks.account
    databricks.workspace = databricks.workspace
  }
}
```

## Required Providers

This module requires TWO Databricks providers:
- `databricks.account` - For account-level resources (metastore)
- `databricks.workspace` - For workspace-level resources (catalog, credentials)

## Storage Architecture

```
Unity Catalog
├── Metastore (metadata only, no storage)
├── Root Storage Location
│   ├── S3 Bucket: bk-uc-root-storage-*
│   ├── Storage Credential
│   ├── IAM Role (dynamically configured)
│   └── Purpose: Workspace catalog data
│
└── External Storage Location
    ├── S3 Bucket: bk-uc-external-*
    ├── Storage Credential
    ├── IAM Role (dynamically configured)
    └── Purpose: External data access
```

## Deployment Sequence

1. Metastore created (independent of workspace)
2. Workspace created (separate module)
3. Metastore assigned to workspace
4. Storage credentials created (generates external_id)
5. IAM roles/policies created (using external_id)
6. Wait 30 seconds for IAM propagation
7. External locations created
8. Workspace catalog created (using root storage)
9. Grants applied

## Outputs

| Output | Description |
|--------|-------------|
| `metastore_id` | Metastore ID |
| `workspace_catalog_name` | Workspace catalog name |
| `root_storage_location_url` | Root storage S3 URL |
| `external_location_url` | External storage S3 URL |

## Notes

- Set `create_workspace_catalog = false` before destroying to cleanly remove resources
- IAM propagation delays are handled automatically
- Storage credentials generate unique external_id for secure IAM trust policies

