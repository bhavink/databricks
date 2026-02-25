# ============================================================================
# AWS Databricks Private Link Deployment - Modular Version
# ============================================================================

terraform {
  required_version = ">= 1.0"

  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.70" # Try latest to see if backend-only issue is fixed
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
  client_id     = var.databricks_client_id
  client_secret = var.databricks_client_secret
}

provider "databricks" {
  alias         = "workspace"
  host          = module.databricks_workspace.workspace_url
  client_id     = var.databricks_client_id
  client_secret = var.databricks_client_secret
}

# ============================================================================
# Random Suffix for Unique Resource Naming
# ============================================================================

resource "random_string" "suffix" {
  length  = 4
  special = false
  upper   = false
}

# ============================================================================
# AWS Data Sources
# ============================================================================

# Get available AZs in the region (excludes local zones)
data "aws_availability_zones" "available" {
  state = "available"

  filter {
    name   = "opt-in-status"
    values = ["opt-in-not-required"]
  }
}

# ============================================================================
# Local Variables and Validation
# ============================================================================

locals {
  prefix         = "${var.prefix}-${random_string.suffix.result}"
  workspace_name = "${var.workspace_name}-${random_string.suffix.result}"

  # Private Link configuration - single flag controls both frontend and backend
  # When enabled: Creates workspace endpoint (UI/API) + relay endpoint (SCC) + VPCE security group
  any_vpce_enabled = var.enable_private_link

  # Auto-select first 2 available AZs if not specified
  # User can override by setting availability_zones variable
  availability_zones = length(var.availability_zones) > 0 ? var.availability_zones : slice(data.aws_availability_zones.available.names, 0, 2)

  # Databricks reserved IP ranges that MUST be avoided
  databricks_reserved_ranges = [
    "127.187.216.0/24", # Databricks internal apps
    "192.168.216.0/24", # Databricks internal apps
    "198.18.216.0/24",  # Databricks internal apps
    "172.17.0.0/16"     # Docker default network (DCS clusters)
  ]

  # Extract first 2 octets from VPC CIDR for validation
  vpc_first_two_octets = join(".", slice(split(".", var.vpc_cidr), 0, 2))

  # Check if VPC CIDR conflicts with Databricks reserved ranges
  vpc_cidr_safe = !contains([
    "127.187",
    "192.168",
    "198.18",
    "172.17"
  ], local.vpc_first_two_octets)
}

# ============================================================================
# Validation
# ============================================================================

# Validate availability zones
resource "terraform_data" "validate_azs" {
  lifecycle {
    precondition {
      condition     = length(local.availability_zones) == 2
      error_message = "Exactly 2 availability zones required for Databricks workspace deployment. Found: ${length(local.availability_zones)} AZs."
    }

    precondition {
      condition     = length(distinct(local.availability_zones)) == 2
      error_message = "Availability zones must be different. Databricks requires 2 distinct AZs. Current AZs: ${join(", ", local.availability_zones)}"
    }
  }
}

# Validate VPC CIDR doesn't conflict with Databricks reserved ranges
resource "terraform_data" "validate_vpc_cidr" {
  lifecycle {
    precondition {
      condition     = local.vpc_cidr_safe
      error_message = <<-EOT
        VPC CIDR ${var.vpc_cidr} conflicts with Databricks reserved IP ranges.

        Reserved ranges to AVOID:
        - 127.187.216.0/24 (Databricks internal applications)
        - 192.168.216.0/24 (Databricks internal applications)
        - 198.18.216.0/24 (Databricks internal applications)
        - 172.17.0.0/16 (Docker default network for DCS clusters)

        Recommended SAFE ranges:
        - 10.0.0.0/8 (e.g., 10.0.0.0/22)
        - 172.16.0.0/12 EXCEPT 172.17.0.0/16 (e.g., 172.18.0.0/22)
        - 192.168.0.0/16 EXCEPT 192.168.216.0/24 (e.g., 192.168.0.0/22)
      EOT
    }
  }
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
  availability_zones       = local.availability_zones

  # VPC Endpoint Configuration
  enable_private_link = var.enable_private_link
  # VPCE service names are auto-detected based on region - only set to override
  workspace_vpce_service = var.workspace_vpce_service
  relay_vpce_service     = var.relay_vpce_service

  databricks_account_id = var.databricks_account_id
  tags                  = var.tags

  providers = {
    databricks.account = databricks.account
  }
}

# ============================================================================
# IAM Module
# NOTE: Created early - cross-account role name needed for KMS workspace CMK policy
# ============================================================================

module "iam" {
  source = "./modules/iam"

  prefix                = local.prefix
  aws_account_id        = var.aws_account_id
  databricks_account_id = var.databricks_account_id
  # Unity Catalog bucket ARNs will be added via depends_on after storage module
  unity_catalog_bucket_arn          = ""
  unity_catalog_external_bucket_arn = ""
  tags                              = var.tags

  providers = {
    databricks.account = databricks.account
  }
}

# ============================================================================
# KMS Module (Optional Encryption)
# NOTE: Uses constructed cross-account role ARN (role created in IAM module)
# ============================================================================

module "kms" {
  source = "./modules/kms"

  prefix                           = local.prefix
  aws_account_id                   = var.aws_account_id
  databricks_account_id            = var.databricks_account_id
  enable_encryption                = var.enable_encryption
  enable_workspace_cmk             = var.enable_workspace_cmk
  existing_workspace_cmk_key_arn   = var.existing_workspace_cmk_key_arn
  existing_workspace_cmk_key_alias = var.existing_workspace_cmk_key_alias
  cmk_admin_arn                    = var.cmk_admin_arn
  kms_key_deletion_window          = var.kms_key_deletion_window
  unity_catalog_role_name          = module.iam.unity_catalog_role_name
  tags                             = var.tags

  depends_on = [
    module.iam # Ensures cross-account role exists before KMS key creation
  ]
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

  # Only create UC root storage bucket when NOT using an existing metastore
  create_uc_root_storage_bucket = var.metastore_id == ""

  providers = {
    databricks.account = databricks.account
  }

  depends_on = [module.kms]
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
  client_id             = var.databricks_client_id
  client_secret         = var.databricks_client_secret

  # From networking module
  vpc_id                      = module.networking.vpc_id
  private_subnet_ids          = module.networking.private_subnet_ids
  workspace_security_group_id = module.networking.workspace_security_group_id

  # VPC Endpoint Configuration
  enable_private_link = var.enable_private_link
  workspace_vpce_id   = module.networking.databricks_workspace_vpce_id
  relay_vpce_id       = module.networking.databricks_relay_vpce_id

  # Private Access Settings
  existing_private_access_settings_id = var.existing_private_access_settings_id
  public_access_enabled               = var.public_access_enabled
  private_access_level                = var.private_access_level

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
  databricks_client_id              = var.databricks_client_id
  databricks_client_secret          = var.databricks_client_secret
  aws_account_id                    = var.aws_account_id
  databricks_account_id             = var.databricks_account_id
  create_workspace_catalog          = var.create_workspace_catalog
  workspace_catalog_name            = var.workspace_catalog_name
  unity_catalog_root_storage_bucket = module.storage.unity_catalog_root_storage_bucket
  unity_catalog_external_bucket     = module.storage.unity_catalog_external_bucket
  enable_encryption                 = var.enable_encryption
  kms_key_arn                       = module.kms.key_arn
  tags                              = var.tags

  # Use existing metastore if provided, otherwise create a new one
  metastore_id = var.metastore_id

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

