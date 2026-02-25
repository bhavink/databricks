# ============================================================================
# VPC Endpoint - Workspace (Frontend - UI/API Access)
# ============================================================================

resource "aws_vpc_endpoint" "workspace" {
  vpc_id              = aws_vpc.databricks_vpc.id
  service_name        = var.workspace_vpce_service
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.privatelink[*].id
  security_group_ids  = [aws_security_group.vpce_sg.id]
  private_dns_enabled = true

  tags = merge(var.tags, {
    Name = "${var.prefix}-workspace-vpce"
  })
}

# ============================================================================
# VPC Endpoint - Relay (Backend - Secure Cluster Connectivity)
# This is CRITICAL for Backend Private Link
# ============================================================================

resource "aws_vpc_endpoint" "relay" {
  vpc_id              = aws_vpc.databricks_vpc.id
  service_name        = var.relay_vpce_service
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.privatelink[*].id
  security_group_ids  = [aws_security_group.vpce_sg.id]
  private_dns_enabled = true

  tags = merge(var.tags, {
    Name = "${var.prefix}-relay-vpce"
  })
}

# ============================================================================
# VPC Endpoint - S3 (Gateway Endpoint - Cost Effective)
# ============================================================================

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

# ============================================================================
# VPC Endpoint - STS (For IAM Role Assumption)
# ============================================================================

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

# ============================================================================
# VPC Endpoint - Kinesis (For Logging and Lineage)
# ============================================================================

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

# ============================================================================
# Register VPC Endpoints with Databricks (Account-Level)
# These resources register the AWS VPC endpoints with Databricks
# ============================================================================

# Register Workspace VPC Endpoint
resource "databricks_mws_vpc_endpoint" "workspace_vpce" {
  provider            = databricks.account
  account_id          = var.databricks_account_id
  vpc_endpoint_name   = "${var.prefix}-workspace-vpce"
  aws_vpc_endpoint_id = aws_vpc_endpoint.workspace.id
  region              = var.region

  depends_on = [aws_vpc_endpoint.workspace]
}

# Register Relay VPC Endpoint (Backend Private Link)
resource "databricks_mws_vpc_endpoint" "relay_vpce" {
  provider            = databricks.account
  account_id          = var.databricks_account_id
  vpc_endpoint_name   = "${var.prefix}-relay-vpce"
  aws_vpc_endpoint_id = aws_vpc_endpoint.relay.id
  region              = var.region

  depends_on = [aws_vpc_endpoint.relay]
}

