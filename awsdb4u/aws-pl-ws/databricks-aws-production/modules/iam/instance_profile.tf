# ============================================================================
# IAM Instance Profile for Databricks Clusters
# ============================================================================

resource "aws_iam_role" "instance_profile_role" {
  name = "${var.prefix}-instance-profile-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(var.tags, {
    Name = "${var.prefix}-instance-profile-role"
  })
}

resource "aws_iam_instance_profile" "instance_profile" {
  name = "${var.prefix}-instance-profile"
  role = aws_iam_role.instance_profile_role.name

  tags = merge(var.tags, {
    Name = "${var.prefix}-instance-profile"
  })
}

# Optional: Add policies for instance profile if needed for data access
resource "aws_iam_policy" "instance_profile_policy" {
  name        = "${var.prefix}-instance-profile-policy"
  description = "Policy for Databricks cluster instance profile"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      # S3 ListBucket permission - only add if external bucket ARN is provided
      var.unity_catalog_external_bucket_arn != "" ? [
        {
          Effect = "Allow"
          Action = [
            "s3:ListBucket"
          ]
          Resource = [
            var.unity_catalog_external_bucket_arn
          ]
        }
      ] : [],
      # S3 GetObject/PutObject permissions - only add if external bucket ARN is provided
      var.unity_catalog_external_bucket_arn != "" ? [
        {
          Effect = "Allow"
          Action = [
            "s3:GetObject",
            "s3:PutObject"
          ]
          Resource = [
            "${var.unity_catalog_external_bucket_arn}/*"
          ]
        }
      ] : [],
      # Placeholder statement if no bucket ARN provided (policy must have at least one statement)
      var.unity_catalog_external_bucket_arn == "" ? [
        {
          Effect = "Allow"
          Action = [
            "sts:GetCallerIdentity"
          ]
          Resource = "*"
        }
      ] : []
    )
  })

  tags = merge(var.tags, {
    Name = "${var.prefix}-instance-profile-policy"
  })
}

resource "aws_iam_role_policy_attachment" "instance_profile" {
  role       = aws_iam_role.instance_profile_role.name
  policy_arn = aws_iam_policy.instance_profile_policy.arn
}

