***REMOVED*** ============================================================================
***REMOVED*** Security Group for Databricks Workspace (Clusters)
***REMOVED*** ============================================================================

resource "aws_security_group" "workspace_sg" {
  name        = "${var.prefix}-workspace-sg"
  description = "Security group for Databricks workspace clusters"
  vpc_id      = aws_vpc.databricks_vpc.id

  tags = merge(var.tags, {
    Name = "${var.prefix}-workspace-sg"
  })
}

***REMOVED*** ============================================================================
***REMOVED*** Workspace Security Group - Ingress Rules
***REMOVED*** ============================================================================

***REMOVED*** Allow internal cluster communication (all TCP)
resource "aws_security_group_rule" "workspace_ingress_tcp" {
  type              = "ingress"
  from_port         = 0
  to_port           = 65535
  protocol          = "tcp"
  self              = true
  security_group_id = aws_security_group.workspace_sg.id
  description       = "Allow internal TCP communication between cluster nodes"
}

***REMOVED*** Allow internal cluster communication (all UDP)
resource "aws_security_group_rule" "workspace_ingress_udp" {
  type              = "ingress"
  from_port         = 0
  to_port           = 65535
  protocol          = "udp"
  self              = true
  security_group_id = aws_security_group.workspace_sg.id
  description       = "Allow internal UDP communication between cluster nodes"
}

***REMOVED*** ============================================================================
***REMOVED*** Workspace Security Group - Egress Rules
***REMOVED*** ============================================================================

***REMOVED*** Self-referencing egress for internal cluster communication
resource "aws_security_group_rule" "workspace_egress_self_tcp" {
  type              = "egress"
  from_port         = 0
  to_port           = 65535
  protocol          = "tcp"
  self              = true
  security_group_id = aws_security_group.workspace_sg.id
  description       = "Allow internal TCP communication between cluster nodes"
}

resource "aws_security_group_rule" "workspace_egress_self_udp" {
  type              = "egress"
  from_port         = 0
  to_port           = 65535
  protocol          = "udp"
  self              = true
  security_group_id = aws_security_group.workspace_sg.id
  description       = "Allow internal UDP communication between cluster nodes"
}

***REMOVED*** Egress to VPC Endpoint Security Group (for Databricks PrivateLink)
***REMOVED*** Only create when Databricks VPC endpoints are enabled
resource "aws_security_group_rule" "workspace_egress_to_vpce_443" {
  count                    = local.any_databricks_vpce_enabled ? 1 : 0
  type                     = "egress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.vpce_sg.id
  security_group_id        = aws_security_group.workspace_sg.id
  description              = "Allow HTTPS to Databricks VPC endpoints"
}

resource "aws_security_group_rule" "workspace_egress_to_vpce_6666" {
  count                    = local.any_databricks_vpce_enabled ? 1 : 0
  type                     = "egress"
  from_port                = 6666
  to_port                  = 6666
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.vpce_sg.id
  security_group_id        = aws_security_group.workspace_sg.id
  description              = "Allow SCC (Secure Cluster Connectivity) to Relay VPC endpoint"
}

resource "aws_security_group_rule" "workspace_egress_to_vpce_8443_8451" {
  count                    = local.any_databricks_vpce_enabled ? 1 : 0
  type                     = "egress"
  from_port                = 8443
  to_port                  = 8451
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.vpce_sg.id
  security_group_id        = aws_security_group.workspace_sg.id
  description              = "Allow control plane and Unity Catalog communication to Databricks VPC endpoints"
}

***REMOVED*** Egress to Internet for library downloads, external data sources, and S3 access
resource "aws_security_group_rule" "workspace_egress_https" {
  type              = "egress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.workspace_sg.id
  description       = "Allow HTTPS for library downloads, external API calls, S3 (DBFS, logs, artifacts)"
}

***REMOVED*** Control plane and Unity Catalog communication (Databricks requirement)
***REMOVED*** NOTE: 0.0.0.0/0 is required by Databricks but does NOT compromise Private Link security
***REMOVED*** - Security groups are PERMISSION filters, NOT routing devices
***REMOVED*** - With Private Link: DNS returns private IP → route table directs to VPC endpoint (stays private)
***REMOVED*** - Without Private Link: DNS returns public IP → route table directs to NAT gateway (goes public)
***REMOVED*** - The 0.0.0.0/0 CIDR allows the traffic but doesn't control the path
***REMOVED*** - See ARCHITECTURE.md for detailed traffic flow sequence diagrams
resource "aws_security_group_rule" "workspace_egress_control_plane" {
  type              = "egress"
  from_port         = 8443
  to_port           = 8451
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.workspace_sg.id
  description       = "Allow control plane API (8443), Unity Catalog (8444), and future extendibility (8445-8451)"
}

***REMOVED*** FIPS encryption support (optional - only if compliance security profile enabled)
resource "aws_security_group_rule" "workspace_egress_fips" {
  type              = "egress"
  from_port         = 2443
  to_port           = 2443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.workspace_sg.id
  description       = "Allow FIPS encryption for compliance security profile (optional)"
}

***REMOVED*** Hive metastore connectivity (LEGACY - NOT USED with Unity Catalog)
***REMOVED*** Unity Catalog workspaces do not require port 3306
resource "aws_security_group_rule" "workspace_egress_mysql" {
  type              = "egress"
  from_port         = 3306
  to_port           = 3306
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.workspace_sg.id
  description       = "Allow MySQL for external metastore connectivity (LEGACY - not used with Unity Catalog)"
}

***REMOVED*** DNS resolution
resource "aws_security_group_rule" "workspace_egress_dns_tcp" {
  type              = "egress"
  from_port         = 53
  to_port           = 53
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.workspace_sg.id
  description       = "Allow DNS resolution (TCP)"
}

resource "aws_security_group_rule" "workspace_egress_dns_udp" {
  type              = "egress"
  from_port         = 53
  to_port           = 53
  protocol          = "udp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.workspace_sg.id
  description       = "Allow DNS resolution (UDP)"
}

***REMOVED*** ============================================================================
***REMOVED*** Security Group for VPC Endpoints
***REMOVED*** Always created for AWS service endpoints (S3/STS/Kinesis) and Databricks VPCEs
***REMOVED*** ============================================================================

resource "aws_security_group" "vpce_sg" {
  name        = "${var.prefix}-vpce-sg"
  description = "Security group for VPC endpoints (AWS services: S3/STS/Kinesis, Databricks: Workspace/Relay)"
  vpc_id      = aws_vpc.databricks_vpc.id

  tags = merge(var.tags, {
    Name = "${var.prefix}-vpce-sg"
  })
}

***REMOVED*** ============================================================================
***REMOVED*** VPC Endpoint Security Group - Ingress Rules
***REMOVED*** Only create when Databricks VPC endpoints are enabled
***REMOVED*** ============================================================================

***REMOVED*** Allow HTTPS from workspace security group (for Databricks + AWS service endpoints)
resource "aws_security_group_rule" "vpce_ingress_https" {
  count                    = local.any_databricks_vpce_enabled ? 1 : 0
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.workspace_sg.id
  security_group_id        = aws_security_group.vpce_sg.id
  description              = "Allow HTTPS from workspace clusters to VPC endpoints"
}

***REMOVED*** Allow SCC port for Relay endpoint (Databricks-specific)
resource "aws_security_group_rule" "vpce_ingress_scc" {
  count                    = local.any_databricks_vpce_enabled ? 1 : 0
  type                     = "ingress"
  from_port                = 6666
  to_port                  = 6666
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.workspace_sg.id
  security_group_id        = aws_security_group.vpce_sg.id
  description              = "Allow SCC from workspace clusters to Relay endpoint"
}

***REMOVED*** Allow control plane and Unity Catalog ports (Databricks-specific)
resource "aws_security_group_rule" "vpce_ingress_control_plane" {
  count                    = local.any_databricks_vpce_enabled ? 1 : 0
  type                     = "ingress"
  from_port                = 8443
  to_port                  = 8451
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.workspace_sg.id
  security_group_id        = aws_security_group.vpce_sg.id
  description              = "Allow control plane and Unity Catalog communication from workspace clusters"
}

***REMOVED*** ============================================================================
***REMOVED*** VPC Endpoint Security Group - Egress Rules
***REMOVED*** Always created (needed for both Databricks and AWS service endpoints)
***REMOVED*** ============================================================================

***REMOVED*** Allow all outbound (to Databricks control plane and AWS services)
resource "aws_security_group_rule" "vpce_egress_all" {
  type              = "egress"
  from_port         = 0
  to_port           = 65535
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.vpce_sg.id
  description       = "Allow all outbound traffic to Databricks control plane and AWS services"
}
