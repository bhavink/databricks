# KMS Module

This module provisions KMS keys for encrypting Databricks S3 buckets (optional).

## Resources Created

### Conditional Resources (when `enable_encryption = true`)
- KMS customer-managed key
- KMS key alias
- KMS key policy with permissions for:
  - AWS account root
  - Databricks cross-account role
  - S3 service

## Usage

```hcl
module "kms" {
  source = "./modules/kms"
  
  prefix                   = "dbx-abc123"
  aws_account_id           = "123456789012"
  cross_account_role_arn   = module.iam.cross_account_role_arn
  enable_encryption        = true
  kms_key_deletion_window  = 30
  
  tags = {
    Environment = "Production"
  }
}
```

## Features

- ✅ Conditional creation (based on `enable_encryption`)
- ✅ Key rotation enabled
- ✅ Configurable deletion window
- ✅ Proper key policy for Databricks and S3 access

## Outputs

| Output | Description |
|--------|-------------|
| `key_id` | KMS key ID (null if disabled) |
| `key_arn` | KMS key ARN (null if disabled) |
| `key_alias` | KMS key alias (null if disabled) |

## Notes

- KMS encryption is optional and controlled by `enable_encryption` variable
- If disabled, S3 buckets use default AES256 encryption
- Key policy allows Databricks cross-account role access
- Key rotation is automatically enabled for security

