# ============================================================================
# UC Root Storage - Storage Credential, IAM, and External Location
# Following SRA pattern for root storage setup
# ============================================================================

# Step 1: Create storage credential for root storage with placeholder role (generates external_id)
resource "databricks_storage_credential" "root_storage" {
  count = var.create_workspace_catalog ? 1 : 0

  provider = databricks.workspace
  name     = "${var.prefix}-root-storage-credential"

  aws_iam_role {
    role_arn = "arn:aws:iam::${var.aws_account_id}:role/${local.uc_root_iam_role_name}"
  }

  comment = "Storage credential for UC root storage"

  depends_on = [
    databricks_metastore_assignment.workspace_assignment
  ]
}

# Step 2: Generate Unity Catalog trust policy using external_id from root storage credential
data "databricks_aws_unity_catalog_assume_role_policy" "root_storage" {
  count = var.create_workspace_catalog ? 1 : 0

  aws_account_id        = var.aws_account_id
  role_name             = local.uc_root_iam_role_name
  unity_catalog_iam_arn = "arn:aws:iam::414351767826:role/unity-catalog-prod-UCMasterRole-14S5ZJVKOTYTL"
  external_id           = databricks_storage_credential.root_storage[0].aws_iam_role[0].external_id
}

# Step 3: Generate Unity Catalog IAM policy for S3 access to UC root storage bucket
data "databricks_aws_unity_catalog_policy" "root_storage" {
  count = var.create_workspace_catalog ? 1 : 0

  aws_account_id = var.aws_account_id
  bucket_name    = var.unity_catalog_root_storage_bucket
  role_name      = local.uc_root_iam_role_name
}

# Step 4: Create IAM policy for root storage
resource "aws_iam_policy" "unity_catalog_root" {
  count = var.create_workspace_catalog ? 1 : 0

  name   = "${var.prefix}-root-storage-policy-${var.workspace_id}"
  policy = data.databricks_aws_unity_catalog_policy.root_storage[0].json

  tags = merge(var.tags, {
    Name = "${var.prefix}-root-storage-policy"
  })
}

# Step 5: Create IAM role for root storage with proper trust policy
resource "aws_iam_role" "unity_catalog_root" {
  count = var.create_workspace_catalog ? 1 : 0

  name               = local.uc_root_iam_role_name
  assume_role_policy = data.databricks_aws_unity_catalog_assume_role_policy.root_storage[0].json

  tags = merge(var.tags, {
    Name = local.uc_root_iam_role_name
  })
}

# Step 6: Attach policy to root storage role
resource "aws_iam_policy_attachment" "unity_catalog_root" {
  count = var.create_workspace_catalog ? 1 : 0

  name       = "unity_catalog_root_policy_attach"
  roles      = [aws_iam_role.unity_catalog_root[0].name]
  policy_arn = aws_iam_policy.unity_catalog_root[0].arn
}

# Step 7: Wait for IAM propagation for root storage
resource "time_sleep" "wait_for_uc_root_iam" {
  count = var.create_workspace_catalog ? 1 : 0

  create_duration = "30s"

  depends_on = [
    aws_iam_policy_attachment.unity_catalog_root
  ]

  # Force replacement when IAM policy changes
  triggers = {
    policy_version = aws_iam_policy.unity_catalog_root[0].id
    role_arn       = aws_iam_role.unity_catalog_root[0].arn
  }
}

# Step 8: Create external location for UC root storage
resource "databricks_external_location" "root_storage" {
  count = var.create_workspace_catalog ? 1 : 0

  provider        = databricks.workspace
  name            = "${var.prefix}-root-storage-location"
  url             = "s3://${var.unity_catalog_root_storage_bucket}/"
  credential_name = databricks_storage_credential.root_storage[0].name
  comment         = "External location for UC root storage"

  # Force recreation when bucket or IAM changes
  lifecycle {
    replace_triggered_by = [
      time_sleep.wait_for_uc_root_iam[0].id
    ]
  }

  depends_on = [
    databricks_storage_credential.root_storage,
    time_sleep.wait_for_uc_root_iam
  ]
}

