# ============================================================================
# VPC Outputs
# ============================================================================

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.databricks_vpc.id
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = aws_vpc.databricks_vpc.cidr_block
}

# ============================================================================
# Subnet Outputs
# ============================================================================

output "private_subnet_ids" {
  description = "Private subnet IDs for Databricks clusters"
  value       = aws_subnet.private[*].id
}

output "privatelink_subnet_ids" {
  description = "PrivateLink subnet IDs for VPC endpoints"
  value       = aws_subnet.privatelink[*].id
}

output "public_subnet_ids" {
  description = "Public subnet IDs for NAT gateways"
  value       = aws_subnet.public[*].id
}

# ============================================================================
# Security Group Outputs
# ============================================================================

output "workspace_security_group_id" {
  description = "Security group ID for Databricks workspace clusters"
  value       = aws_security_group.workspace_sg.id
}

output "vpce_security_group_id" {
  description = "Security group ID for VPC endpoints"
  value       = aws_security_group.vpce_sg.id
}

# ============================================================================
# VPC Endpoint Outputs (AWS Resources)
# ============================================================================

output "workspace_vpce_id" {
  description = "AWS VPC Endpoint ID for Workspace (frontend)"
  value       = aws_vpc_endpoint.workspace.id
}

output "relay_vpce_id" {
  description = "AWS VPC Endpoint ID for Relay (backend SCC)"
  value       = aws_vpc_endpoint.relay.id
}

output "s3_vpce_id" {
  description = "AWS VPC Endpoint ID for S3"
  value       = aws_vpc_endpoint.s3.id
}

output "sts_vpce_id" {
  description = "AWS VPC Endpoint ID for STS"
  value       = aws_vpc_endpoint.sts.id
}

output "kinesis_vpce_id" {
  description = "AWS VPC Endpoint ID for Kinesis"
  value       = aws_vpc_endpoint.kinesis.id
}

# ============================================================================
# Databricks MWS VPC Endpoint Outputs (Registered with Databricks)
# ============================================================================

output "databricks_workspace_vpce_id" {
  description = "Databricks MWS workspace VPC endpoint ID (for workspace configuration)"
  value       = databricks_mws_vpc_endpoint.workspace_vpce.vpc_endpoint_id
}

output "databricks_relay_vpce_id" {
  description = "Databricks MWS relay VPC endpoint ID (for workspace configuration)"
  value       = databricks_mws_vpc_endpoint.relay_vpce.vpc_endpoint_id
}

# ============================================================================
# Gateway and Routing Outputs
# ============================================================================

output "internet_gateway_id" {
  description = "Internet Gateway ID"
  value       = aws_internet_gateway.igw.id
}

output "nat_gateway_ids" {
  description = "NAT Gateway IDs"
  value       = aws_nat_gateway.nat[*].id
}

