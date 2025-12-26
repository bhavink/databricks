# ============================================================================
# Databricks Account Configuration Variables
# ============================================================================

variable "databricks_account_id" {
  description = "Databricks account ID (found in account console)"
  type        = string
}

variable "client_id" {
  description = "Databricks service principal client ID (OAuth)"
  type        = string
}

variable "client_secret" {
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
  description = "Availability zones for subnets"
  type        = list(string)
  default     = ["us-west-2a", "us-west-2b"]
}

# ============================================================================
# VPC Endpoint Service Names (Region-Specific)
# ============================================================================

variable "workspace_vpce_service" {
  description = "Databricks workspace VPC endpoint service name (region-specific). Find your region's service name at: https://docs.databricks.com/resources/supported-regions.html"
  type        = string
}

variable "relay_vpce_service" {
  description = "Databricks relay (SCC) VPC endpoint service name (region-specific). Find your region's service name at: https://docs.databricks.com/resources/supported-regions.html"
  type        = string
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

variable "cmk_admin_arn" {
  description = "ARN of the IAM user/role that will administer the CMK (defaults to account root if not specified)"
  type        = string
  default     = null
}

# ============================================================================
# Private Access Settings
# ============================================================================

variable "public_access_enabled" {
  description = "Allow public access to the workspace (set to false for fully private workspace)"
  type        = bool
  default     = true
}

variable "private_access_level" {
  description = "Private access level for backend communication (ACCOUNT or ENDPOINT)"
  type        = string
  default     = "ENDPOINT"
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

