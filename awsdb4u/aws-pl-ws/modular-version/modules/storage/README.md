# Storage Module

This module provisions all S3 buckets for Databricks workspace and Unity Catalog.

## Resources Created

### 1. Workspace Root Storage Bucket
- DBFS root storage for the workspace
- Versioning enabled
- Server-side encryption (AES256 or KMS)
- Databricks-generated bucket policy for access

### 2. Unity Catalog Metastore Bucket
- Storage for UC metastore metadata
- Versioning enabled
- Server-side encryption

### 3. Unity Catalog External Location Bucket
- Storage for external data
- Used by workspace catalog's external location
- Versioning enabled

### 4. Unity Catalog Root Storage Bucket
- Dedicated storage for workspace catalog
- Primary data storage for workspace catalog
- Versioning enabled

## Usage

```hcl
module "storage" {
  source = "./modules/storage"
  
  prefix                                  = "dbx-abc123"
  suffix                                  = "jp6k"
  databricks_account_id                   = "743862e4-fdac-4504-a9cc-2d69bd1605e8"
  root_storage_bucket_name                = "bk-root"
  unity_catalog_bucket_name               = "bk-uc-metastore"
  unity_catalog_external_bucket_name      = "bk-uc-external"
  unity_catalog_root_storage_bucket_name  = "bk-uc-root-storage"
  enable_encryption                       = false
  kms_key_arn                             = null
  
  tags = {
    Environment = "Production"
  }
  
  providers = {
    databricks.account = databricks.account
  }
}
```

## Outputs

| Output | Description |
|--------|-------------|
| `root_storage_bucket` | Workspace root storage bucket name |
| `unity_catalog_bucket` | UC metastore bucket name |
| `unity_catalog_external_bucket` | UC external location bucket name |
| `unity_catalog_root_storage_bucket` | UC root storage bucket name |

## Features

- ✅ All buckets have versioning enabled
- ✅ Public access blocked on all buckets
- ✅ Force destroy enabled for easy cleanup
- ✅ Optional KMS encryption
- ✅ Databricks-generated bucket policy for root storage

