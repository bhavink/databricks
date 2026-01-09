# ============================================================================
# Databricks Account Configuration Variables
# ============================================================================

variable "databricks_account_id" {
  description = "Databricks account ID (found in account console)"
  type        = string
}

variable "databricks_client_id" {
  description = "Databricks service principal client ID (OAuth)"
  type        = string
}

variable "databricks_client_secret" {
  description = "Databricks service principal client secret (OAuth)"
  type        = string
  sensitive   = true
}

variable "aws_account_id" {
  description = "AWS account ID where resources will be deployed"
  type        = string
}

variable "aws_profile" {
  description = "AWS CLI profile name to use for authentication (leave empty to use default credentials or environment variables)"
  type        = string
  default     = ""
}

# ============================================================================
# Workspace Configuration
# ============================================================================

variable "workspace_name" {
  description = "Name of the Databricks workspace"
  type        = string
  default     = "databricks-privatelink-workspace"
}

variable "prefix" {
  description = "Prefix for resource names (will have random suffix added)"
  type        = string
  default     = "dbx"
}

variable "region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-west-2"
}

# ============================================================================
# Network Configuration
# ============================================================================

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/22"
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets (Databricks clusters) - /24 recommended"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "privatelink_subnet_cidrs" {
  description = "CIDR blocks for PrivateLink subnets (VPC endpoints) - /26 sufficient for VPC endpoints"
  type        = list(string)
  default     = ["10.0.3.0/26", "10.0.3.64/26"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets (NAT gateways) - /26 sufficient for NAT gateways"
  type        = list(string)
  default     = ["10.0.0.0/26", "10.0.0.64/26"]
}

variable "availability_zones" {
  description = "Availability zones for subnets (must be exactly 2 zones). Leave empty to auto-select first 2 available AZs in the region."
  type        = list(string)
  default     = []

  validation {
    condition     = length(var.availability_zones) == 0 || length(var.availability_zones) == 2
    error_message = "If specifying availability_zones, must provide exactly 2 zones. Leave empty for auto-detection."
  }

  validation {
    condition     = length(var.availability_zones) == 0 || length(distinct(var.availability_zones)) == length(var.availability_zones)
    error_message = "Availability zones must be unique (no duplicates allowed)."
  }
}

# ============================================================================
# VPC Endpoint Service Names (Region-Specific)
# ============================================================================

variable "enable_private_link" {
  description = <<-EOT
    Enable AWS PrivateLink for Databricks (both workspace UI/API and cluster connectivity).
    - true: Creates workspace and relay VPC endpoints - all traffic uses Private Link (recommended for security)
    - false: All traffic uses public internet via NAT gateway (lower cost, less secure)

    When enabled, creates:
    - Workspace VPC endpoint (for UI/API access on ports 443, 8443-8451)
    - Relay VPC endpoint (for Secure Cluster Connectivity/SCC on port 6666)
    - Private Access Settings (controls frontend public access behavior)
    - VPC endpoint security group and all required rules

    When disabled:
    - NO Databricks Private Link VPC endpoints created
    - Workspace UI/API accessed via public internet (through NAT gateway)
    - Cluster traffic uses public internet (through NAT gateway)
    - S3, STS, and Kinesis VPC endpoints still created (cost optimization)
  EOT
  type        = bool
  default     = true
}

variable "workspace_vpce_service" {
  description = "Databricks workspace VPC endpoint service name (region-specific). OPTIONAL - Auto-detected based on region. Only set this to override the default for your region (e.g., for GovCloud DoD endpoints). See: https://docs.databricks.com/resources/supported-regions.html"
  type        = string
  default     = ""
}

variable "relay_vpce_service" {
  description = "Databricks relay (SCC) VPC endpoint service name (region-specific). OPTIONAL - Auto-detected based on region. Only set this to override the default for your region (e.g., for GovCloud DoD endpoints). See: https://docs.databricks.com/resources/supported-regions.html"
  type        = string
  default     = ""
}

# ============================================================================
# S3 Bucket Configuration
# ============================================================================

variable "root_storage_bucket_name" {
  description = "S3 bucket name for Databricks root storage (must be globally unique)"
  type        = string
}

variable "unity_catalog_bucket_name" {
  description = "S3 bucket name for Unity Catalog metastore (must be globally unique)"
  type        = string
}

variable "unity_catalog_external_bucket_name" {
  description = "S3 bucket name for Unity Catalog external location (must be globally unique)"
  type        = string
}

variable "unity_catalog_root_storage_bucket_name" {
  description = "S3 bucket name for Unity Catalog root storage (must be globally unique)"
  type        = string
}

# ============================================================================
# Security Configuration
# ============================================================================

variable "enable_encryption" {
  description = "Enable KMS encryption for S3 buckets and EBS volumes"
  type        = bool
  default     = false
}

variable "kms_key_deletion_window" {
  description = "KMS key deletion window in days"
  type        = number
  default     = 30
}

# ============================================================================
# Workspace Customer Managed Keys (Optional)
# ============================================================================

variable "enable_workspace_cmk" {
  description = "Enable Customer Managed Keys for workspace storage (DBFS, EBS) and managed services encryption"
  type        = bool
  default     = false
}

variable "existing_workspace_cmk_key_arn" {
  description = <<-EOT
    OPTIONAL: Existing KMS key ARN to use for workspace CMK (instead of creating new key).
    
    Use this when:
    - You have a pre-created KMS key with proper Databricks policies
    - You want to share the same key across multiple workspaces
    - Your organization requires centralized key management
    
    When provided:
    - Skips KMS key creation
    - Uses this existing key for workspace encryption
    - Still requires enable_workspace_cmk = true
    
    When empty (default):
    - Creates new KMS key (if enable_workspace_cmk = true)
    
    Key policy requirements:
    - Must allow Databricks account (414351767826) for DBFS/managed services
    - Must allow cross-account role for EBS encryption
    - See docs/WORKSPACE_CMK_EXPLAINED.md for details
    
    Example: "arn:aws:kms:us-west-1:872515275153:key/abc12345-6789-..."
  EOT
  type        = string
  default     = ""
}

variable "existing_workspace_cmk_key_alias" {
  description = "OPTIONAL: Existing KMS key alias (required if existing_workspace_cmk_key_arn is provided). Example: 'alias/my-databricks-key'"
  type        = string
  default     = ""
}

variable "cmk_admin_arn" {
  description = "ARN of the IAM user/role that will administer the CMK (defaults to account root if not specified). Only used when creating new keys."
  type        = string
  default     = null
}

# ============================================================================
# Private Access Settings
# NOTE: PAS is an ACCOUNT-LEVEL object that can be SHARED across multiple workspaces
# ============================================================================

variable "existing_private_access_settings_id" {
  description = <<-EOT
    OPTIONAL: Existing Private Access Settings ID to reuse across multiple workspaces.

    Architecture Note:
    - PAS is an ACCOUNT-LEVEL object that can be attached to MULTIPLE workspaces
    - Controls FRONTEND Private Link behavior (public_access_enabled)
    - Typically shared when multiple workspaces use the same transit VPC

    Multi-Workspace Deployment Pattern:
    1. First workspace: Leave empty (module creates new PAS, output PAS ID)
    2. Second+ workspaces: Set to PAS ID from first workspace (reuses existing PAS)

    Example:
      # First workspace
      existing_private_access_settings_id = ""  # Creates new PAS

      # Second workspace (reuses PAS from first)
      existing_private_access_settings_id = "pas-abc123"  # From first workspace output

    Network Configuration is always created (one per workspace, cannot be shared).
  EOT
  type        = string
  default     = ""
}

variable "public_access_enabled" {
  description = <<-EOT
    Controls public internet access to workspace UI/API when Private Link is enabled.

    Use Cases:
    - enable_private_link=true + public_access_enabled=false:
      Maximum security - All access via Private Link only, no public internet access
    - enable_private_link=true + public_access_enabled=true:
      Hybrid access - Private Link available but public access also allowed (with optional IP ACLs)
    - enable_private_link=false:
      This setting is ignored - workspace is publicly accessible via NAT gateway

    Default: true (allows public access alongside Private Link for flexibility)
  EOT
  type        = bool
  default     = true
}

variable "private_access_level" {
  description = "Private access level for backend communication. ACCOUNT = public relay (default), ENDPOINT = uses backend VPC endpoint. Set to ENDPOINT only when backend VPC endpoint is enabled and tested."
  type        = string
  default     = "ACCOUNT"
}

# ============================================================================
# User Management
# ============================================================================

variable "workspace_admin_email" {
  description = "Email address for workspace admin user"
  type        = string
  default     = "bhavin.kukadia@databricks.com"
}

variable "create_workspace_catalog" {
  description = "Whether to create workspace catalog with external location (set to false to skip for clean destroy)"
  type        = bool
  default     = true
}

variable "workspace_catalog_name" {
  description = "Custom name prefix for the workspace catalog. If provided, will be used as: <catalog_name>_<prefix>_catalog. If empty, will use: <prefix>_catalog"
  type        = string
  default     = ""
}

variable "metastore_id" {
  description = "Existing Unity Catalog metastore ID. If provided, the module will use this metastore instead of creating a new one. Root storage bucket and IAM resources will also be skipped."
  type        = string
  default     = ""
}

# ============================================================================
# IP Access Lists (Optional Security Feature)
# ============================================================================

variable "enable_ip_access_lists" {
  description = "Enable IP access lists for workspace security"
  type        = bool
  default     = false
}

variable "allowed_ip_addresses" {
  description = "List of allowed IP addresses/CIDR ranges for workspace access (required if enable_ip_access_lists is true)"
  type        = list(string)
  default     = []
}

# ============================================================================
# Tags
# ============================================================================

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}

