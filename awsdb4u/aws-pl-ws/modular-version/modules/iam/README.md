***REMOVED*** IAM Module

This module provisions IAM roles and policies for Databricks workspace and Unity Catalog.

***REMOVED******REMOVED*** Resources Created

***REMOVED******REMOVED******REMOVED*** 1. Cross-Account Role
- IAM role for Databricks control plane access
- Uses Databricks-generated assume role policy
- Cross-account policy for workspace management

***REMOVED******REMOVED******REMOVED*** 2. Unity Catalog Metastore Role
- IAM role for Unity Catalog metastore access
- S3 bucket access for metastore storage
- Trust policy with Databricks UC service principal

***REMOVED******REMOVED******REMOVED*** 3. Instance Profile
- IAM role for EC2 instances (Databricks clusters)
- Instance profile for cluster compute
- Optional S3 access policy for data operations

***REMOVED******REMOVED*** Usage

```hcl
module "iam" {
  source = "./modules/iam"
  
  prefix                             = "dbx-abc123"
  aws_account_id                     = "123456789012"
  databricks_account_id              = "743862e4-fdac-4504-a9cc-2d69bd1605e8"
  unity_catalog_bucket_arn           = module.storage.unity_catalog_bucket_arn
  unity_catalog_external_bucket_arn  = module.storage.unity_catalog_external_bucket_arn
  
  tags = {
    Environment = "Production"
  }
  
  providers = {
    databricks.account = databricks.account
  }
}
```

***REMOVED******REMOVED*** Outputs

| Output | Description |
|--------|-------------|
| `cross_account_role_arn` | Cross-account role ARN |
| `unity_catalog_role_arn` | UC metastore role ARN |
| `instance_profile_arn` | Cluster instance profile ARN |

***REMOVED******REMOVED*** Dependencies

This module depends on:
- Storage module outputs (bucket ARNs)
- Databricks account provider

***REMOVED******REMOVED*** Notes

- Cross-account role uses Databricks-generated policies
- Root storage access managed via S3 bucket policy (not IAM)
- Unity Catalog workspace-level IAM resources created in UC module
- Wait time after creation recommended for IAM propagation

