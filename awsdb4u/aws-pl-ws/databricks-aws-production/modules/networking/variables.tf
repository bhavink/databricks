# ============================================================================
# Required Variables
# ============================================================================

variable "prefix" {
  description = "Prefix for resource naming (with random suffix)"
  type        = string
}

variable "region" {
  description = "AWS region for deployment"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets (Databricks clusters)"
  type        = list(string)
}

variable "privatelink_subnet_cidrs" {
  description = "CIDR blocks for PrivateLink subnets (VPC endpoints)"
  type        = list(string)
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets (NAT gateways)"
  type        = list(string)
}

variable "availability_zones" {
  description = "Availability zones for subnets"
  type        = list(string)
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# ============================================================================
# VPC Endpoint Configuration
# ============================================================================

variable "enable_private_link" {
  description = "Enable Databricks Private Link (creates workspace and relay VPC endpoints)"
  type        = bool
  default     = true
}

variable "workspace_vpce_service" {
  description = "Databricks workspace VPC endpoint service name (region-specific). OPTIONAL - Auto-detected based on region. Only set to override. See: https://docs.databricks.com/resources/supported-regions.html"
  type        = string
  default     = ""
}

variable "relay_vpce_service" {
  description = "Databricks relay (SCC) VPC endpoint service name (region-specific). OPTIONAL - Auto-detected based on region. Only set to override. See: https://docs.databricks.com/resources/supported-regions.html"
  type        = string
  default     = ""
}

variable "databricks_account_id" {
  description = "Databricks account ID for registering VPC endpoints"
  type        = string
}

# ============================================================================
# ============================================================================
