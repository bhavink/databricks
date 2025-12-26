***REMOVED*** ============================================================================
***REMOVED*** KMS Module - Provider Configuration
***REMOVED*** ============================================================================

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

***REMOVED*** Data source for current region
data "aws_region" "current" {}

***REMOVED*** ============================================================================
***REMOVED*** KMS Key for S3 Bucket Encryption (Optional)
***REMOVED*** Used for encrypting S3 buckets (root storage, Unity Catalog)
***REMOVED*** ============================================================================

resource "aws_kms_key" "databricks" {
  count                   = var.enable_encryption ? 1 : 0
  description             = "KMS key for Databricks S3 bucket encryption"
  deletion_window_in_days = var.kms_key_deletion_window
  enable_key_rotation     = true

  tags = merge(var.tags, {
    Name = "${var.prefix}-kms-key"
  })
}

resource "aws_kms_alias" "databricks" {
  count         = var.enable_encryption ? 1 : 0
  name          = "alias/${var.prefix}-databricks"
  target_key_id = aws_kms_key.databricks[0].key_id
}

resource "aws_kms_key_policy" "databricks" {
  count  = var.enable_encryption ? 1 : 0
  key_id = aws_kms_key.databricks[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${var.aws_account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow Databricks Account to use the key"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::414351767826:root"  ***REMOVED*** Databricks AWS account
        }
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey",
          "kms:CreateGrant"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = "s3.${data.aws_region.current.name}.amazonaws.com"
          }
        }
      },
      {
        Sid    = "Allow S3 to use the key"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = "*"
      }
    ]
  })
}

***REMOVED*** ============================================================================
***REMOVED*** Customer Managed Keys for Workspace (Optional)
***REMOVED*** Based on SRA pattern: https://github.com/databricks/terraform-databricks-sra/blob/main/aws/tf/cmk.tf
***REMOVED*** Single key encrypts workspace storage (DBFS, EBS) and managed services (control plane)
***REMOVED*** ============================================================================

locals {
  cmk_admin_arn             = var.cmk_admin_arn != null ? var.cmk_admin_arn : "arn:aws:iam::${var.aws_account_id}:root"
  databricks_aws_account_id = "414351767826" ***REMOVED*** Databricks AWS account ID for all regions
  ***REMOVED*** Construct cross-account role ARN to avoid circular dependency
  cross_account_role_arn    = "arn:aws:iam::${var.aws_account_id}:role/${var.prefix}-crossaccount"
}

***REMOVED*** KMS Key for Workspace (DBFS, EBS, and Managed Services)
resource "aws_kms_key" "workspace_storage" {
  count = var.enable_workspace_cmk ? 1 : 0

  description             = "KMS key for Databricks workspace (DBFS, EBS, and managed services)"
  deletion_window_in_days = var.kms_key_deletion_window
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Id      = "key-policy-workspace"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = [local.cmk_admin_arn]
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow Databricks to use KMS key for DBFS and managed services"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${local.databricks_aws_account_id}:root"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:PrincipalTag/DatabricksAccountId" = [var.databricks_account_id]
          }
        }
      },
      {
        Sid    = "Allow Databricks to use KMS key for EBS"
        Effect = "Allow"
        Principal = {
          AWS = local.cross_account_role_arn
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey*",
          "kms:CreateGrant",
          "kms:DescribeKey"
        ]
        Resource = "*"
        Condition = {
          "ForAnyValue:StringLike" = {
            "kms:ViaService" = "ec2.*.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = merge(var.tags, {
    Name = "${var.prefix}-workspace-key"
  })
}

resource "aws_kms_alias" "workspace_storage" {
  count = var.enable_workspace_cmk ? 1 : 0

  name          = "alias/${var.prefix}-workspace-key"
  target_key_id = aws_kms_key.workspace_storage[0].key_id
}

