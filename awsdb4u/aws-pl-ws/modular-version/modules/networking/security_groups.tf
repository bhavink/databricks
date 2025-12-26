# ============================================================================
# Security Group for Databricks Workspace (Clusters)
# ============================================================================

resource "aws_security_group" "workspace_sg" {
  name        = "${var.prefix}-workspace-sg"
  description = "Security group for Databricks workspace clusters"
  vpc_id      = aws_vpc.databricks_vpc.id

  tags = merge(var.tags, {
    Name = "${var.prefix}-workspace-sg"
  })
}

# ============================================================================
# Workspace Security Group - Ingress Rules
# ============================================================================

# Allow internal cluster communication (all TCP)
resource "aws_security_group_rule" "workspace_ingress_tcp" {
  type              = "ingress"
  from_port         = 0
  to_port           = 65535
  protocol          = "tcp"
  self              = true
  security_group_id = aws_security_group.workspace_sg.id
  description       = "Allow internal TCP communication between cluster nodes"
}

# Allow internal cluster communication (all UDP)
resource "aws_security_group_rule" "workspace_ingress_udp" {
  type              = "ingress"
  from_port         = 0
  to_port           = 65535
  protocol          = "udp"
  self              = true
  security_group_id = aws_security_group.workspace_sg.id
  description       = "Allow internal UDP communication between cluster nodes"
}

# ============================================================================
# Workspace Security Group - Egress Rules
# ============================================================================

# Self-referencing egress for internal cluster communication
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

# Egress to VPC Endpoint Security Group (for PrivateLink)
resource "aws_security_group_rule" "workspace_egress_to_vpce_443" {
  type                     = "egress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.vpce_sg.id
  security_group_id        = aws_security_group.workspace_sg.id
  description              = "Allow HTTPS to VPC endpoints"
}

resource "aws_security_group_rule" "workspace_egress_to_vpce_6666" {
  type                     = "egress"
  from_port                = 6666
  to_port                  = 6666
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.vpce_sg.id
  security_group_id        = aws_security_group.workspace_sg.id
  description              = "Allow SCC (Secure Cluster Connectivity) to Relay VPC endpoint"
}

resource "aws_security_group_rule" "workspace_egress_to_vpce_8443_8451" {
  type                     = "egress"
  from_port                = 8443
  to_port                  = 8451
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.vpce_sg.id
  security_group_id        = aws_security_group.workspace_sg.id
  description              = "Allow control plane and Unity Catalog communication to VPC endpoints"
}

# Egress to Internet for library downloads, external data sources, and S3 access
resource "aws_security_group_rule" "workspace_egress_https" {
  type              = "egress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.workspace_sg.id
  description       = "Allow HTTPS for library downloads, external API calls, S3 (DBFS, logs, artifacts)"
}

resource "aws_security_group_rule" "workspace_egress_mysql" {
  type              = "egress"
  from_port         = 3306
  to_port           = 3306
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.workspace_sg.id
  description       = "Allow MySQL for external metastore connectivity"
}

# DNS resolution
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

# ============================================================================
# Security Group for VPC Endpoints
# ============================================================================

resource "aws_security_group" "vpce_sg" {
  name        = "${var.prefix}-vpce-sg"
  description = "Security group for VPC endpoints (Workspace, Relay, STS, Kinesis)"
  vpc_id      = aws_vpc.databricks_vpc.id

  tags = merge(var.tags, {
    Name = "${var.prefix}-vpce-sg"
  })
}

# ============================================================================
# VPC Endpoint Security Group - Ingress Rules
# ============================================================================

# Allow HTTPS from workspace security group
resource "aws_security_group_rule" "vpce_ingress_https" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.workspace_sg.id
  security_group_id        = aws_security_group.vpce_sg.id
  description              = "Allow HTTPS from workspace clusters"
}

# Allow SCC port for Relay endpoint
resource "aws_security_group_rule" "vpce_ingress_scc" {
  type                     = "ingress"
  from_port                = 6666
  to_port                  = 6666
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.workspace_sg.id
  security_group_id        = aws_security_group.vpce_sg.id
  description              = "Allow SCC from workspace clusters to Relay endpoint"
}

# Allow control plane and Unity Catalog ports
resource "aws_security_group_rule" "vpce_ingress_control_plane" {
  type                     = "ingress"
  from_port                = 8443
  to_port                  = 8451
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.workspace_sg.id
  security_group_id        = aws_security_group.vpce_sg.id
  description              = "Allow control plane and Unity Catalog communication from workspace clusters"
}

# ============================================================================
# VPC Endpoint Security Group - Egress Rules
# ============================================================================

# Allow all outbound (to Databricks control plane)
resource "aws_security_group_rule" "vpce_egress_all" {
  type              = "egress"
  from_port         = 0
  to_port           = 65535
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.vpce_sg.id
  description       = "Allow all outbound traffic to Databricks control plane"
}

