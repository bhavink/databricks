***REMOVED*** ============================================================================
***REMOVED*** VPC Endpoint - Workspace (Required for Both Frontend AND Backend Private Link)
***REMOVED*** - Frontend Private Link: Used for UI/API access by users
***REMOVED*** - Backend Private Link: Used for cluster REST API calls to control plane
***REMOVED*** ============================================================================

resource "aws_vpc_endpoint" "workspace" {
  count               = local.any_databricks_vpce_enabled ? 1 : 0
  vpc_id              = aws_vpc.databricks_vpc.id
  service_name        = local.computed_workspace_vpce_service
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.privatelink[*].id
  security_group_ids  = [aws_security_group.vpce_sg.id]
  private_dns_enabled = true

  tags = merge(var.tags, {
    Name = "${var.prefix}-workspace-vpce"
  })

  lifecycle {
    precondition {
      condition     = local.computed_workspace_vpce_service != ""
      error_message = "Region '${var.region}' does not have a workspace VPC endpoint service configured. Either use a supported region or manually set workspace_vpce_service variable. Supported regions: ${join(", ", keys(local.vpce_service_names))}"
    }
  }
}

***REMOVED*** ============================================================================
***REMOVED*** VPC Endpoint - Relay (Backend - Secure Cluster Connectivity)
***REMOVED*** This is CRITICAL for Backend Private Link
***REMOVED*** ============================================================================

resource "aws_vpc_endpoint" "relay" {
  count               = var.enable_private_link ? 1 : 0
  vpc_id              = aws_vpc.databricks_vpc.id
  service_name        = local.computed_relay_vpce_service
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.privatelink[*].id
  security_group_ids  = [aws_security_group.vpce_sg.id]
  private_dns_enabled = true

  tags = merge(var.tags, {
    Name = "${var.prefix}-relay-vpce"
  })

  lifecycle {
    precondition {
      condition     = local.computed_relay_vpce_service != ""
      error_message = "Region '${var.region}' does not have a relay VPC endpoint service configured. Either use a supported region or manually set relay_vpce_service variable. Supported regions: ${join(", ", keys(local.vpce_service_names))}"
    }
  }
}

***REMOVED*** ============================================================================
***REMOVED*** VPC Endpoint - S3 (Gateway Endpoint - FREE!)
***REMOVED*** Always created to reduce NAT gateway data transfer costs
***REMOVED*** ============================================================================

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.databricks_vpc.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids = concat(
    [aws_route_table.public.id],
    aws_route_table.private[*].id,
    [aws_route_table.privatelink.id]
  )

  tags = merge(var.tags, {
    Name = "${var.prefix}-s3-vpce"
  })
}

***REMOVED*** ============================================================================
***REMOVED*** VPC Endpoint - STS (For IAM Role Assumption)
***REMOVED*** Always created to reduce NAT gateway costs and improve security
***REMOVED*** ============================================================================

resource "aws_vpc_endpoint" "sts" {
  vpc_id              = aws_vpc.databricks_vpc.id
  service_name        = "com.amazonaws.${var.region}.sts"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.privatelink[*].id
  security_group_ids  = [aws_security_group.vpce_sg.id]
  private_dns_enabled = true

  tags = merge(var.tags, {
    Name = "${var.prefix}-sts-vpce"
  })
}

***REMOVED*** ============================================================================
***REMOVED*** VPC Endpoint - Kinesis (For Logging and Lineage)
***REMOVED*** Always created to reduce NAT gateway costs
***REMOVED*** ============================================================================

resource "aws_vpc_endpoint" "kinesis" {
  vpc_id              = aws_vpc.databricks_vpc.id
  service_name        = "com.amazonaws.${var.region}.kinesis-streams"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.privatelink[*].id
  security_group_ids  = [aws_security_group.vpce_sg.id]
  private_dns_enabled = true

  tags = merge(var.tags, {
    Name = "${var.prefix}-kinesis-vpce"
  })
}

***REMOVED*** ============================================================================
***REMOVED*** Register VPC Endpoints with Databricks (Account-Level)
***REMOVED*** These resources register the AWS VPC endpoints with Databricks
***REMOVED*** ============================================================================

***REMOVED*** Register Workspace VPC Endpoint (Required for both Frontend and Backend Private Link)
resource "databricks_mws_vpc_endpoint" "workspace_vpce" {
  count               = local.any_databricks_vpce_enabled ? 1 : 0
  provider            = databricks.account
  account_id          = var.databricks_account_id
  vpc_endpoint_name   = "${var.prefix}-workspace-vpce"
  aws_vpc_endpoint_id = aws_vpc_endpoint.workspace[0].id
  region              = var.region

  depends_on = [aws_vpc_endpoint.workspace]
}

***REMOVED*** Register Relay VPC Endpoint (Backend Private Link)
resource "databricks_mws_vpc_endpoint" "relay_vpce" {
  count               = var.enable_private_link ? 1 : 0
  provider            = databricks.account
  account_id          = var.databricks_account_id
  vpc_endpoint_name   = "${var.prefix}-relay-vpce"
  aws_vpc_endpoint_id = aws_vpc_endpoint.relay[0].id
  region              = var.region

  depends_on = [aws_vpc_endpoint.relay]
}
