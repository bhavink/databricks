***REMOVED*** ============================================================================
***REMOVED*** VPC Outputs
***REMOVED*** ============================================================================

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.databricks_vpc.id
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = aws_vpc.databricks_vpc.cidr_block
}

***REMOVED*** ============================================================================
***REMOVED*** Subnet Outputs
***REMOVED*** ============================================================================

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

***REMOVED*** ============================================================================
***REMOVED*** Security Group Outputs
***REMOVED*** ============================================================================

output "workspace_security_group_id" {
  description = "Security group ID for Databricks workspace clusters"
  value       = aws_security_group.workspace_sg.id
}

output "vpce_security_group_id" {
  description = "Security group ID for VPC endpoints"
  value       = aws_security_group.vpce_sg.id
}

***REMOVED*** ============================================================================
***REMOVED*** VPC Endpoint Outputs (AWS Resources)
***REMOVED*** ============================================================================

output "workspace_vpce_id" {
  description = "AWS VPC Endpoint ID for Workspace (null if disabled)"
  value       = local.any_databricks_vpce_enabled ? aws_vpc_endpoint.workspace[0].id : null
}

output "relay_vpce_id" {
  description = "AWS VPC Endpoint ID for Relay (null if disabled)"
  value       = var.enable_private_link ? aws_vpc_endpoint.relay[0].id : null
}

output "s3_vpce_id" {
  description = "AWS VPC Endpoint ID for S3 (always created to reduce NAT costs)"
  value       = aws_vpc_endpoint.s3.id
}

output "sts_vpce_id" {
  description = "AWS VPC Endpoint ID for STS (always created to reduce NAT costs)"
  value       = aws_vpc_endpoint.sts.id
}

output "kinesis_vpce_id" {
  description = "AWS VPC Endpoint ID for Kinesis (always created to reduce NAT costs)"
  value       = aws_vpc_endpoint.kinesis.id
}

***REMOVED*** ============================================================================
***REMOVED*** Databricks MWS VPC Endpoint Outputs (Registered with Databricks)
***REMOVED*** ============================================================================

output "databricks_workspace_vpce_id" {
  description = "Databricks MWS workspace VPC endpoint ID (for workspace configuration, null if disabled)"
  value       = local.any_databricks_vpce_enabled ? databricks_mws_vpc_endpoint.workspace_vpce[0].vpc_endpoint_id : null
}

output "databricks_relay_vpce_id" {
  description = "Databricks MWS relay VPC endpoint ID (for workspace configuration, null if disabled)"
  value       = var.enable_private_link ? databricks_mws_vpc_endpoint.relay_vpce[0].vpc_endpoint_id : null
}

***REMOVED*** ============================================================================
***REMOVED*** Gateway and Routing Outputs
***REMOVED*** ============================================================================

output "internet_gateway_id" {
  description = "Internet Gateway ID"
  value       = aws_internet_gateway.igw.id
}

output "nat_gateway_ids" {
  description = "NAT Gateway IDs"
  value       = aws_nat_gateway.nat[*].id
}
