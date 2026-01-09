***REMOVED*** ============================================================================
***REMOVED*** IAM Role Outputs
***REMOVED*** ============================================================================

output "cross_account_role_arn" {
  description = "Cross-account IAM role ARN for Databricks"
  value       = aws_iam_role.cross_account_role.arn
}

output "cross_account_role_name" {
  description = "Cross-account IAM role name"
  value       = aws_iam_role.cross_account_role.name
}

output "unity_catalog_role_arn" {
  description = "Unity Catalog metastore IAM role ARN"
  value       = aws_iam_role.unity_catalog_role.arn
}

output "unity_catalog_role_name" {
  description = "Unity Catalog metastore IAM role name"
  value       = aws_iam_role.unity_catalog_role.name
}

output "instance_profile_arn" {
  description = "Instance profile ARN for Databricks clusters"
  value       = aws_iam_instance_profile.instance_profile.arn
}

output "instance_profile_name" {
  description = "Instance profile name"
  value       = aws_iam_instance_profile.instance_profile.name
}

