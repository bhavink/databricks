***REMOVED*** ============================================================================
***REMOVED*** UC External Storage - Storage Credential, IAM, and External Location
***REMOVED*** Following SRA pattern for external storage setup
***REMOVED*** ============================================================================

***REMOVED*** Step 1: Create storage credential with placeholder role (generates external_id)
resource "databricks_storage_credential" "external_storage" {
  count = var.create_workspace_catalog ? 1 : 0

  provider = databricks.workspace
  name     = "${var.prefix}-external-storage-credential"

  aws_iam_role {
    role_arn = "arn:aws:iam::${var.aws_account_id}:role/${local.uc_iam_role_name}"
  }

  comment = "Storage credential for external location"

  depends_on = [
    databricks_metastore_assignment.workspace_assignment
  ]
}

***REMOVED*** Step 2: Generate Unity Catalog trust policy using external_id from storage credential
data "databricks_aws_unity_catalog_assume_role_policy" "external_location" {
  count = var.create_workspace_catalog ? 1 : 0

  aws_account_id        = var.aws_account_id
  role_name             = local.uc_iam_role_name
  unity_catalog_iam_arn = "arn:aws:iam::414351767826:role/unity-catalog-prod-UCMasterRole-14S5ZJVKOTYTL"
  external_id           = databricks_storage_credential.external_storage[0].aws_iam_role[0].external_id
}

***REMOVED*** Step 3: Generate Unity Catalog IAM policy for S3 access
data "databricks_aws_unity_catalog_policy" "external_location" {
  count = var.create_workspace_catalog ? 1 : 0

  aws_account_id = var.aws_account_id
  bucket_name    = var.unity_catalog_external_bucket
  role_name      = local.uc_iam_role_name
}

***REMOVED*** Step 4: Create IAM policy
resource "aws_iam_policy" "unity_catalog_external" {
  count = var.create_workspace_catalog ? 1 : 0

  name   = "${var.prefix}-catalog-policy-${var.workspace_id}"
  policy = data.databricks_aws_unity_catalog_policy.external_location[0].json

  tags = merge(var.tags, {
    Name = "${var.prefix}-catalog-policy"
  })
}

***REMOVED*** Step 5: Create IAM role with proper trust policy
resource "aws_iam_role" "unity_catalog_external" {
  count = var.create_workspace_catalog ? 1 : 0

  name               = local.uc_iam_role_name
  assume_role_policy = data.databricks_aws_unity_catalog_assume_role_policy.external_location[0].json

  tags = merge(var.tags, {
    Name = local.uc_iam_role_name
  })
}

***REMOVED*** Step 6: Attach policy to role
resource "aws_iam_policy_attachment" "unity_catalog_external" {
  count = var.create_workspace_catalog ? 1 : 0

  name       = "unity_catalog_external_policy_attach"
  roles      = [aws_iam_role.unity_catalog_external[0].name]
  policy_arn = aws_iam_policy.unity_catalog_external[0].arn
}

***REMOVED*** Step 7: Wait for IAM propagation
resource "time_sleep" "wait_for_uc_iam" {
  count = var.create_workspace_catalog ? 1 : 0

  create_duration = "30s"

  depends_on = [
    aws_iam_policy_attachment.unity_catalog_external
  ]
}

***REMOVED*** ============================================================================
***REMOVED*** External Location
***REMOVED*** ============================================================================

resource "databricks_external_location" "external_location" {
  count = var.create_workspace_catalog ? 1 : 0

  provider        = databricks.workspace
  name            = "${var.prefix}-external-location"
  url             = "s3://${var.unity_catalog_external_bucket}/"
  credential_name = databricks_storage_credential.external_storage[0].name
  comment         = "External location for Unity Catalog"

  depends_on = [
    databricks_storage_credential.external_storage,
    time_sleep.wait_for_uc_iam
  ]
}

