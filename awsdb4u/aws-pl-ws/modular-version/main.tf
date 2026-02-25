# ============================================================================
# AWS Databricks Private Link Deployment - Modular Version
# ============================================================================

terraform {
  required_version = ">= 1.0"

  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.50"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.9"
    }
  }
}

# ============================================================================
# Providers
# ============================================================================

provider "aws" {
  region = var.region

  # Option 1: Use named AWS CLI profile (recommended for local development)
  profile = var.aws_profile

  # Option 2: Use default AWS CLI credentials or environment variables
  # Comment out the 'profile' line above and Terraform will automatically use:
  # - AWS CLI default credentials (aws configure)
  # - AWS SSO session (aws sso login)
  # - Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN)
}

provider "databricks" {
  alias         = "account"
  host          = "https://accounts.cloud.databricks.com"
  account_id    = var.databricks_account_id
  client_id     = var.client_id
  client_secret = var.client_secret
}

provider "databricks" {
  alias         = "workspace"
  host          = module.databricks_workspace.workspace_url
  client_id     = var.client_id
  client_secret = var.client_secret
}

# ============================================================================
# Random Suffix for Unique Resource Naming
# ============================================================================

resource "random_string" "suffix" {
  length  = 4
  special = false
  upper   = false
}

locals {
  prefix         = "${var.prefix}-${random_string.suffix.result}"
  workspace_name = "${var.workspace_name}-${random_string.suffix.result}"
}

# ============================================================================
# Networking Module
# ============================================================================

module "networking" {
  source = "./modules/networking"

  prefix                   = local.prefix
  region                   = var.region
  vpc_cidr                 = var.vpc_cidr
  private_subnet_cidrs     = var.private_subnet_cidrs
  privatelink_subnet_cidrs = var.privatelink_subnet_cidrs
  public_subnet_cidrs      = var.public_subnet_cidrs
  availability_zones       = var.availability_zones
  workspace_vpce_service   = var.workspace_vpce_service
  relay_vpce_service       = var.relay_vpce_service
  databricks_account_id    = var.databricks_account_id
  tags                     = var.tags

  providers = {
    databricks.account = databricks.account
  }
}

# ============================================================================
# KMS Module (Optional Encryption)
# NOTE: Created early to avoid circular dependencies
# ============================================================================

module "kms" {
  source = "./modules/kms"

  prefix                  = local.prefix
  aws_account_id          = var.aws_account_id
  databricks_account_id   = var.databricks_account_id
  enable_encryption       = var.enable_encryption
  enable_workspace_cmk    = var.enable_workspace_cmk
  cmk_admin_arn           = var.cmk_admin_arn
  kms_key_deletion_window = var.kms_key_deletion_window
  tags                    = var.tags
}

# ============================================================================
# Storage Module
# ============================================================================

module "storage" {
  source = "./modules/storage"

  prefix                                 = local.prefix
  suffix                                 = random_string.suffix.result
  databricks_account_id                  = var.databricks_account_id
  root_storage_bucket_name               = var.root_storage_bucket_name
  unity_catalog_bucket_name              = var.unity_catalog_bucket_name
  unity_catalog_external_bucket_name     = var.unity_catalog_external_bucket_name
  unity_catalog_root_storage_bucket_name = var.unity_catalog_root_storage_bucket_name
  enable_encryption                      = var.enable_encryption
  kms_key_arn                            = module.kms.key_arn
  tags                                   = var.tags

  providers = {
    databricks.account = databricks.account
  }

  depends_on = [module.kms]
}

# ============================================================================
# IAM Module
# ============================================================================

module "iam" {
  source = "./modules/iam"

  prefix                            = local.prefix
  aws_account_id                    = var.aws_account_id
  databricks_account_id             = var.databricks_account_id
  unity_catalog_bucket_arn          = module.storage.unity_catalog_bucket_arn
  unity_catalog_external_bucket_arn = module.storage.unity_catalog_external_bucket_arn
  tags                              = var.tags

  providers = {
    databricks.account = databricks.account
  }

  depends_on = [module.storage]
}

# ============================================================================
# Databricks Workspace Module
# ============================================================================

module "databricks_workspace" {
  source = "./modules/databricks_workspace"

  prefix                = local.prefix
  workspace_name        = local.workspace_name
  region                = var.region
  databricks_account_id = var.databricks_account_id
  workspace_admin_email = var.workspace_admin_email
  client_id             = var.client_id
  client_secret         = var.client_secret

  # From networking module
  vpc_id                      = module.networking.vpc_id
  private_subnet_ids          = module.networking.private_subnet_ids
  workspace_security_group_id = module.networking.workspace_security_group_id
  workspace_vpce_id           = module.networking.databricks_workspace_vpce_id
  relay_vpce_id               = module.networking.databricks_relay_vpce_id

  # Private Access Settings
  public_access_enabled = var.public_access_enabled
  private_access_level  = var.private_access_level

  # From storage module
  root_storage_bucket = module.storage.root_storage_bucket

  # From IAM module
  cross_account_role_arn = module.iam.cross_account_role_arn

  # IP Access Lists (Optional)
  enable_ip_access_lists = var.enable_ip_access_lists
  allowed_ip_addresses   = var.allowed_ip_addresses

  # Workspace CMK (Optional) - Single key for both storage and managed services
  enable_workspace_cmk        = var.enable_workspace_cmk
  workspace_storage_key_arn   = module.kms.workspace_storage_key_arn
  workspace_storage_key_alias = module.kms.workspace_storage_key_alias

  tags = var.tags

  providers = {
    databricks.account   = databricks.account
    databricks.workspace = databricks.workspace
  }

  depends_on = [
    module.networking,
    module.storage,
    module.iam,
    module.kms
  ]
}

# ============================================================================
# Unity Catalog Module
# ============================================================================

module "unity_catalog" {
  source = "./modules/unity_catalog"

  prefix                            = local.prefix
  region                            = var.region
  workspace_name                    = local.workspace_name
  workspace_id                      = module.databricks_workspace.workspace_id
  workspace_admin_email             = var.workspace_admin_email
  client_id                         = var.client_id
  client_secret                     = var.client_secret
  aws_account_id                    = var.aws_account_id
  databricks_account_id             = var.databricks_account_id
  create_workspace_catalog          = var.create_workspace_catalog
  unity_catalog_root_storage_bucket = module.storage.unity_catalog_root_storage_bucket
  unity_catalog_external_bucket     = module.storage.unity_catalog_external_bucket
  tags                              = var.tags

  providers = {
    databricks.account   = databricks.account
    databricks.workspace = databricks.workspace
  }

  depends_on = [
    module.databricks_workspace,
    module.storage
  ]
}

# ============================================================================
# User Assignment Module (Workspace Admin)
# Assigns existing Databricks account user as workspace admin
# Reference: https://github.com/databricks/terraform-databricks-sra/tree/main/aws/tf/modules/databricks_account/user_assignment
# ============================================================================

module "user_assignment" {
  source = "./modules/user_assignment"
  count  = var.workspace_admin_email != "" ? 1 : 0

  user_name    = var.workspace_admin_email
  workspace_id = module.databricks_workspace.workspace_id

  providers = {
    databricks = databricks.account
  }

  depends_on = [
    module.unity_catalog.metastore_assignment_id
  ]
}

