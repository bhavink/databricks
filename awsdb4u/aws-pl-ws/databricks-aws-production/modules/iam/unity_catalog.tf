# ============================================================================
# IAM Role - Unity Catalog Metastore
# ============================================================================

resource "aws_iam_role" "unity_catalog_role" {
  name = "${var.prefix}-unity-catalog-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::414351767826:role/unity-catalog-prod-UCMasterRole-14S5ZJVKOTYTL"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "sts:ExternalId" = var.databricks_account_id
          }
        }
      }
    ]
  })

  tags = merge(var.tags, {
    Name = "${var.prefix}-unity-catalog-role"
  })
}

resource "aws_iam_policy" "unity_catalog_policy" {
  name        = "${var.prefix}-unity-catalog-policy"
  description = "Policy for Unity Catalog metastore bucket access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      # S3 access statement - only add if bucket ARNs are provided
      var.unity_catalog_bucket_arn != "" ? [
        {
          Effect = "Allow"
          Action = [
            "s3:GetObject",
            "s3:PutObject",
            "s3:DeleteObject",
            "s3:ListBucket",
            "s3:GetBucketLocation"
          ]
          Resource = [
            var.unity_catalog_bucket_arn,
            "${var.unity_catalog_bucket_arn}/*"
          ]
        }
      ] : [],
      # AssumeRole statement - always included
      [
        {
          Effect = "Allow"
          Action = [
            "sts:AssumeRole"
          ]
          Resource = [
            "arn:aws:iam::${var.aws_account_id}:role/${var.prefix}-unity-catalog-role"
          ]
        }
      ]
    )
  })

  tags = merge(var.tags, {
    Name = "${var.prefix}-unity-catalog-policy"
  })
}

resource "aws_iam_role_policy_attachment" "unity_catalog" {
  role       = aws_iam_role.unity_catalog_role.name
  policy_arn = aws_iam_policy.unity_catalog_policy.arn
}

