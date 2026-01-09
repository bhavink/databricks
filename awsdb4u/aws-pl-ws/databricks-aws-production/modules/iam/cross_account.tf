***REMOVED*** ============================================================================
***REMOVED*** IAM Module - Provider Configuration
***REMOVED*** ============================================================================

terraform {
  required_providers {
    databricks = {
      source                = "databricks/databricks"
      version               = "~> 1.0"
      configuration_aliases = [databricks.account]
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

***REMOVED*** ============================================================================
***REMOVED*** Data Source - Databricks Cross-Account Role External ID
***REMOVED*** ============================================================================

data "databricks_aws_assume_role_policy" "cross_account" {
  provider    = databricks.account
  external_id = var.databricks_account_id
}

data "databricks_aws_crossaccount_policy" "cross_account" {
  provider = databricks.account
}

***REMOVED*** ============================================================================
***REMOVED*** IAM Role - Databricks Cross-Account Role
***REMOVED*** ============================================================================

resource "aws_iam_role" "cross_account_role" {
  name               = "${var.prefix}-cross-account-role"
  assume_role_policy = data.databricks_aws_assume_role_policy.cross_account.json

  tags = merge(var.tags, {
    Name = "${var.prefix}-cross-account-role"
  })
}

resource "aws_iam_role_policy" "cross_account_policy" {
  name   = "${var.prefix}-cross-account-policy"
  role   = aws_iam_role.cross_account_role.id
  policy = data.databricks_aws_crossaccount_policy.cross_account.json
}

***REMOVED*** Note: S3 access for workspace root storage is managed via bucket policy
***REMOVED*** not via IAM role policies attached to the cross-account role

